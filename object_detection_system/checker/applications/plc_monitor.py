import logging
import base64
import copy
import os
import tempfile
import sys
import threading
import time
import json
from pathlib import Path
from urllib import error as urlerror, request

import yaml
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from websockets.sync.client import connect as websocket_connect


THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[3]
DJANGO_ROOT = THIS_FILE.parents[2]
SETTINGS_PATH = PROJECT_ROOT / "settings" / "plc_settings.yaml"
LOCK_PATH = Path(tempfile.gettempdir()) / "object_detection_system_plc_monitor.lock"

if str(DJANGO_ROOT) not in sys.path:
    sys.path.insert(0, str(DJANGO_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "object_detection_system.settings")

import django  # noqa: E402
from django.apps import apps  # noqa: E402

if not apps.ready and not getattr(apps, "loading", False):
    django.setup()

from checker.applications.snap_service import SnapResult, is_snap_running  # noqa: E402


logger = logging.getLogger(__name__)
_background_thread = None
_latest_plc_result = None
_latest_plc_result_lock = threading.Lock()


class AlreadyRunningError(RuntimeError):
    pass


class SingleInstanceLock:
    def __init__(self, path=LOCK_PATH):
        self.path = Path(path)
        self.file = None
        self._locked_by = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, "a+")

        if os.name == "nt":
            try:
                import msvcrt

                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
                self._locked_by = "msvcrt"
            except OSError as exc:
                self.file.close()
                self.file = None
                raise AlreadyRunningError(f"PLC monitor is already running. lock={self.path}") from exc
        else:
            try:
                import fcntl

                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._locked_by = "fcntl"
            except BlockingIOError as exc:
                self.file.close()
                self.file = None
                raise AlreadyRunningError(f"PLC monitor is already running. lock={self.path}") from exc

        self.file.seek(0)
        self.file.truncate()
        self.file.write(str(os.getpid()))
        self.file.flush()
        return self

    def release(self):
        if self.file is None:
            return
        try:
            if self._locked_by == "msvcrt":
                import msvcrt

                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            elif self._locked_by == "fcntl":
                import fcntl

                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        finally:
            self.file.close()
            self.file = None
            self._locked_by = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc, tb):
        self.release()


class PlcClient:
    """Adapter around the finscommand package (OMRON FINS/UDP)."""

    # FINSメモリエリアコード（ビットアクセス用）
    BIT_AREA_CODES = {
        "CIO": 0x30,
        "W": 0x31,
        "H": 0x32,
        "A": 0x33,
        "D": 0x02,
    }

    def __init__(self, connection_config):
        try:
            from finscommand import fins
        except ImportError as exc:
            raise RuntimeError("finscommand がインストールされていません。依存関係をインストールしてください。") from exc

        class _FinsUdpClient(fins):
            # finscommand 0.1.3 の __del__ は sock.cloase() の誤記で
            # AttributeError になるため、ここで安全にソケットを閉じる
            def __del__(self):
                sock = getattr(self, "sock", None)
                if sock is not None:
                    sock.close()

        self._client_class = _FinsUdpClient
        self.config = connection_config
        self.client = None

    def connect(self):
        host = self.config["host"]
        port = int(self.config.get("port", 9600))
        timeout = float(self.config.get("timeout", 2.0))

        dest_fins = self._fins_address(self.config.get("plc_node"), default="0.0.0")
        src_fins = self._fins_address(self.config.get("pc_node"), default="0.127.0")

        self.client = self._client_class(host, dest_fins, src_fins, timeout)
        # finscommand はポート9600固定のため、設定値で上書きする
        self.client.addr = (host, port)
        return self

    def close(self):
        if self.client is None:
            return
        try:
            self.client.sock.close()
        finally:
            self.client = None

    def read_bit(self, area, word_address, bit):
        command = self._bit_command(b"\x01\x01", area, word_address, bit)
        response = self.client.SendCommand(command)
        # レスポンス = FINSヘッダ10byte + コマンドエコー2byte + 終了コード2byte + データ
        if len(response) < 15:
            raise RuntimeError(f"PLCからのビット読取レスポンスが不正です: {response.hex()}")
        return bool(response[14])

    def write_bit(self, area, word_address, bit, value):
        command = self._bit_command(b"\x01\x02", area, word_address, bit)
        command.append(1 if int(value) else 0)
        self.client.SendCommand(command)

    def _bit_command(self, command_code, area, word_address, bit):
        command = bytearray(8)
        command[0:2] = command_code
        command[2] = self._bit_area_code(area)
        command[3:5] = int(word_address).to_bytes(2, "big")
        command[5] = int(bit)
        command[6:8] = (1).to_bytes(2, "big")
        return command

    @classmethod
    def _bit_area_code(cls, area):
        area_name = str(area or "CIO").upper()
        if area_name.startswith("E") and len(area_name) >= 2 and area_name[1:2].isalnum() and area_name not in cls.BIT_AREA_CODES:
            # EMエリアはバンク番号付き（例: E0, E1, ... EA）
            return 0x20 + int(area_name[1:], 16)
        code = cls.BIT_AREA_CODES.get(area_name)
        if code is None:
            raise RuntimeError(f"未対応のPLCメモリエリアです: {area}")
        return code

    @staticmethod
    def _fins_address(node, default):
        if node is None:
            return default
        return f"0.{int(node)}.0"


class TestServerPlcClient:
    """HTTP client for the root-level plc_test_server.py."""

    def __init__(self, test_server_config):
        self.config = test_server_config
        self.base_url = test_server_config.get("base_url", "http://127.0.0.1:8010").rstrip("/")

    def connect(self):
        return self

    def close(self):
        return None

    def read_bit(self, area, word_address, bit):
        url = f"{self.base_url}/api/bit/{area}/{int(word_address)}/{int(bit)}"
        with request.urlopen(url, timeout=float(self.config.get("timeout", 3.0))) as response:
            data = json.loads(response.read().decode("utf-8"))
        return bool(data["value"])

    def write_bit(self, area, word_address, bit, value):
        url = f"{self.base_url}/api/bit"
        body = json.dumps({
            "area": area,
            "word_address": int(word_address),
            "bit": int(bit),
            "value": int(value),
        }).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=float(self.config.get("timeout", 3.0))) as response:
            response.read()


def load_config(path=SETTINGS_PATH):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def is_plc_enabled(config):
    return bool(config.get("plc", {}).get("enabled", True))


def is_test_server_enabled(config):
    return bool(config.get("test_server", {}).get("enabled", False))


def build_plc_client(config):
    if is_plc_enabled(config):
        return PlcClient(config["connection"]).connect()
    if is_test_server_enabled(config):
        return TestServerPlcClient(config["test_server"]).connect()
    return None


def _signal_address(signal):
    return signal["area"], signal["word_address"], signal["bit"]


def notify_checker_status(payload):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        "checker_status",
        {
            "type": "send_checker_status",
            "payload": payload,
        },
    )


def set_latest_plc_result(payload):
    global _latest_plc_result
    with _latest_plc_result_lock:
        _latest_plc_result = copy.deepcopy(payload)


def get_latest_plc_result():
    with _latest_plc_result_lock:
        return copy.deepcopy(_latest_plc_result)


def clear_latest_plc_result():
    global _latest_plc_result
    with _latest_plc_result_lock:
        _latest_plc_result = None


def _read_signal(client, signal, default=False):
    if not signal:
        return default
    return client.read_bit(*_signal_address(signal))


def _write_signal_value(client, signal, value):
    if not signal:
        return None
    client.write_bit(*_signal_address(signal), int(value))
    return int(value)


def clear_runtime_signals(client, monitor, result_signal):
    client.write_bit(monitor["area"], monitor["word_address"], monitor["bit"], 0)
    if not result_signal:
        return
    for name in ("complete", "ok", "error"):
        _write_signal_value(client, result_signal.get(name), 0)


def write_completed_result_signals(client, result_signal, is_ok):
    if not result_signal:
        return

    ok_signal = result_signal.get("ok")
    error_signal = result_signal.get("error")
    complete_signal = result_signal.get("complete")

    ok_value = 1 if is_ok else 0
    error_value = 0 if is_ok else 1
    complete_value = 0 if is_ok else 1

    if ok_signal:
        value = _write_signal_value(client, ok_signal, ok_value)
        logger.info("PLC result OK signal set: %s%s.%02d=%s", ok_signal["area"], int(ok_signal["word_address"]), int(ok_signal["bit"]), value)
    if error_signal:
        value = _write_signal_value(client, error_signal, error_value)
        logger.info("PLC result error signal set: %s%s.%02d=%s", error_signal["area"], int(error_signal["word_address"]), int(error_signal["bit"]), value)
    if complete_signal:
        value = _write_signal_value(client, complete_signal, complete_value)
        logger.info("PLC result complete signal set: %s%s.%02d=%s", complete_signal["area"], int(complete_signal["word_address"]), int(complete_signal["bit"]), value)


def write_error_result_signals(client, result_signal):
    if not result_signal:
        return

    error_signal = result_signal.get("error")
    complete_signal = result_signal.get("complete")

    if error_signal:
        value = _write_signal_value(client, error_signal, 1)
        logger.info("PLC result error signal set: %s%s.%02d=%s", error_signal["area"], int(error_signal["word_address"]), int(error_signal["bit"]), value)
    if complete_signal:
        value = _write_signal_value(client, complete_signal, 1)
        logger.info("PLC result complete signal set after error: %s%s.%02d=%s", complete_signal["area"], int(complete_signal["word_address"]), int(complete_signal["bit"]), value)


def reset_result_signals(config=None):
    config = config or load_config()
    client = build_plc_client(config)
    if client is None:
        logger.info("PLC and test server are disabled by settings. Result signal reset is skipped.")
        clear_latest_plc_result()
        return [{
            "name": "plc",
            "skipped": True,
            "reason": "PLC and test server are disabled in settings/plc_settings.yaml",
        }]

    result_signal = config.get("result_signal")
    if not result_signal:
        clear_latest_plc_result()
        return []

    reset_targets = []
    try:
        monitor = config.get("monitor")
        if monitor:
            client.write_bit(monitor["area"], monitor["word_address"], monitor["bit"], 0)
            reset_targets.append({
                "name": "trigger",
                "area": monitor["area"],
                "word_address": int(monitor["word_address"]),
                "bit": int(monitor["bit"]),
                "value": 0,
            })
        for name in ("complete", "ok", "error"):
            signal = result_signal.get(name)
            if not signal:
                continue
            value = 1 if name == "complete" else 0
            _write_signal_value(client, signal, value)
            reset_targets.append({
                "name": name,
                "area": signal["area"],
                "word_address": int(signal["word_address"]),
                "bit": int(signal["bit"]),
                "value": value,
            })
    finally:
        client.close()
    clear_latest_plc_result()
    return reset_targets


def get_confirm_websocket_url(config):
    checker_api = config.get("checker_api", {})
    return checker_api.get("confirm_ws_url", "ws://127.0.0.1:8000/checker/ws/confirm/")


def run_checker_confirm_api(config=None):
    config = config or load_config()
    checker_api = config.get("checker_api", {})
    url = get_confirm_websocket_url(config)
    timeout = float(checker_api.get("timeout", 60.0))
    request_payload = {
        "snap": "True",
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "plc_monitor",
    }

    logger.info("Calling checker confirm WebSocket API: %s", url)
    image_bytes = None
    result_payload = None

    with websocket_connect(
        url,
        open_timeout=timeout,
        close_timeout=timeout,
        max_size=None,
    ) as websocket:
        websocket.send(json.dumps(request_payload))
        for _ in range(2):
            message = websocket.recv(timeout=timeout)
            if isinstance(message, bytes):
                image_bytes = message
                continue

            data = json.loads(message)
            if data.get("error"):
                raise RuntimeError(data["error"])
            result_payload = data

    if image_bytes is None or result_payload is None:
        raise RuntimeError("checker confirm WebSocket API did not return image and result payload")

    return SnapResult(
        message=result_payload.get("message", ""),
        timestamp=result_payload.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S")),
        result_dict=result_payload.get("result_dict", {}),
        result=bool(result_payload.get("result")),
        image_bytes=image_bytes,
    )


def run_monitor():
    config = load_config()
    client = build_plc_client(config)
    if client is None:
        logger.info("PLC monitor is disabled. Set plc.enabled=true or test_server.enabled=true in settings/plc_settings.yaml.")
        return

    monitor = config["monitor"]
    result_signal = config.get("result_signal")
    poll_interval = float(monitor.get("poll_interval_seconds", 1.0))
    last_connection_error_log = 0.0

    # 起動インターロック: 電源再投入などでPLCに古いtrigger=ONが残っていても、
    # 一度trigger=OFFを確認するまで検査を受け付けない
    startup_armed = False
    startup_wait_logged = False
    previous_trigger = None

    logger.info(
        "PLC monitor started: %s%s.%02d",
        monitor["area"],
        int(monitor["word_address"]),
        int(monitor["bit"]),
    )

    try:
        while True:
            try:
                if is_snap_running():
                    logger.info("Judgment is already running. PLC polling is paused.")
                    time.sleep(poll_interval)
                    continue

                is_on = client.read_bit(monitor["area"], monitor["word_address"], monitor["bit"])

                if not startup_armed:
                    if is_on:
                        if not startup_wait_logged:
                            logger.warning(
                                "PLC trigger is already ON at startup. Waiting for trigger=OFF before accepting requests."
                            )
                            startup_wait_logged = True
                    else:
                        startup_armed = True
                        previous_trigger = False
                        logger.info("PLC trigger is OFF. Startup interlock released. Trigger requests are now accepted.")
                    time.sleep(poll_interval)
                    continue

                rising_edge = is_on and previous_trigger is False
                previous_trigger = is_on

                if rising_edge:
                    complete_is_on = _read_signal(client, result_signal.get("complete") if result_signal else None, True)
                    if not complete_is_on:
                        logger.warning("PLC trigger ignored because complete is OFF. Resetting trigger bit.")
                        client.write_bit(monitor["area"], monitor["word_address"], monitor["bit"], 0)
                        previous_trigger = False
                        time.sleep(poll_interval)
                        continue

                    logger.info("PLC trigger rising edge detected. Monitoring is paused while judgment is running.")
                    clear_runtime_signals(client, monitor, result_signal)
                    try:
                        snap_result = run_checker_confirm_api(config)
                    except Exception as exc:
                        client.write_bit(monitor["area"], monitor["word_address"], monitor["bit"], 0)
                        write_error_result_signals(client, result_signal)
                        payload = {
                            "type": "plc_status",
                            "status": "error",
                            "error": "PLCトリガーによる判定に失敗しました: " + str(exc),
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        }
                        set_latest_plc_result(payload)
                        notify_checker_status(payload)
                        raise

                    logger.info("Snap backend completed: result=%s result_dict=%s", snap_result.result, snap_result.result_dict)
                    client.write_bit(monitor["area"], monitor["word_address"], monitor["bit"], 0)
                    write_completed_result_signals(client, result_signal, snap_result.result)
                    payload = {
                        "type": "plc_status",
                        "status": "completed",
                        "result": snap_result.result,
                        "result_dict": snap_result.result_dict,
                        "message": snap_result.message,
                        "timestamp": snap_result.timestamp,
                        "image_data_url": "data:image/png;base64," + base64.b64encode(snap_result.image_bytes).decode("ascii"),
                    }
                    set_latest_plc_result(payload)
                    notify_checker_status(payload)
            except urlerror.URLError as exc:
                now = time.monotonic()
                if now - last_connection_error_log >= 30.0:
                    logger.warning("PLC/test server is not reachable yet: %s", exc)
                    last_connection_error_log = now
            except Exception:
                logger.exception("PLC monitor iteration failed. Trigger/result bits were not fully updated.")

            time.sleep(poll_interval)
    finally:
        client.close()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        with SingleInstanceLock():
            run_monitor()
    except AlreadyRunningError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc


def start_background_monitor():
    global _background_thread
    if _background_thread and _background_thread.is_alive():
        return _background_thread

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    def target():
        try:
            with SingleInstanceLock():
                run_monitor()
        except AlreadyRunningError as exc:
            logger.info("PLC monitor background thread is not started: %s", exc)
        except Exception:
            logger.exception("PLC monitor background thread stopped unexpectedly.")

    _background_thread = threading.Thread(target=target, name="plc-monitor", daemon=True)
    _background_thread.start()
    logger.info("PLC monitor background thread started.")
    return _background_thread


if __name__ == "__main__":
    main()

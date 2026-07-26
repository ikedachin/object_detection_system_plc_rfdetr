import io
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from asgiref.sync import async_to_sync
from django.test import Client, TestCase, override_settings
from PIL import Image

from checker.applications.detect import detect_objects
from checker.applications import plc_monitor
from checker.applications.get_img import StillCamera
from checker.applications.rfdetr_model import resolve_project_root_path
from checker.applications.snap_service import encode_png_from_rgb_array


class FakeDetections:
    xyxy = np.array([[10.0, 20.0, 50.0, 70.0]])
    confidence = np.array([0.91])
    class_id = np.array([0])
    data = {"class_name": np.array(["part"])}


class FakeRfdetrModel:
    def __init__(self):
        self.calls = []

    def predict(self, image, threshold):
        self.calls.append((image.size, threshold))
        return FakeDetections()


class RfdetrDetectObjectsTests(TestCase):
    def test_detect_objects_converts_rfdetr_detections(self):
        model = FakeRfdetrModel()
        image = Image.new("RGB", (100, 100), (255, 255, 255))

        result_dict, image_array = async_to_sync(detect_objects)(
            image,
            model,
            conf=0.7,
            class_names=["part"],
        )

        self.assertEqual(result_dict, {"part": 1})
        self.assertEqual(model.calls, [((100, 100), 0.7)])
        self.assertEqual(image_array.shape, (100, 100, 3))


class ResolveProjectRootPathTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tmp.name) / "object_detection_system_plc_rfdetr"
        self.override = override_settings(PROJECT_ROOT=self.project_root)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        self.tmp.cleanup()

    def test_relative_path_is_resolved_under_project_root(self):
        result = resolve_project_root_path("projects/demo/models/checkpoint.pth")

        self.assertEqual(result, self.project_root / "projects/demo/models/checkpoint.pth")

    def test_native_absolute_path_is_returned_without_prefixing_project_root(self):
        absolute_path = self.project_root / "projects/demo/models/checkpoint.pth"

        result = resolve_project_root_path(absolute_path)

        self.assertEqual(result, absolute_path)

    def test_windows_project_path_is_rebased_to_current_project_root(self):
        result = resolve_project_root_path(
            r"C:\Users\user\object_detection_system_plc_rfdetr\projects\demo\models\checkpoint.pth"
        )

        self.assertEqual(result, self.project_root / "projects/demo/models/checkpoint.pth")

    def test_windows_settings_path_is_rebased_to_current_project_root(self):
        result = resolve_project_root_path(r"C:\Users\user\repo\settings\rfdetr_detect.yaml")

        self.assertEqual(result, self.project_root / "settings/rfdetr_detect.yaml")


class LatestPlcResultTests(TestCase):
    def tearDown(self):
        plc_monitor.clear_latest_plc_result()

    def test_latest_plc_result_api_returns_null_before_result(self):
        plc_monitor.clear_latest_plc_result()

        response = Client().get("/checker/api/latest_plc_result/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True, "result": None})

    def test_latest_plc_result_api_returns_saved_payload_copy(self):
        payload = {
            "type": "plc_status",
            "status": "completed",
            "timestamp": "2026-06-24T12:00:00",
            "result": True,
            "result_dict": {"part": 1},
            "image_data_url": "data:image/png;base64,abc",
        }
        plc_monitor.set_latest_plc_result(payload)
        payload["result_dict"]["part"] = 99

        response = Client().get("/checker/api/latest_plc_result/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"]["result_dict"], {"part": 1})


class SnapImageEncodingTests(TestCase):
    def test_rgb_array_is_encoded_without_red_blue_swap(self):
        rgb_image = np.array([[[255, 0, 0]]], dtype=np.uint8)

        png_bytes = encode_png_from_rgb_array(rgb_image)
        decoded = Image.open(io.BytesIO(png_bytes)).convert("RGB")

        self.assertEqual(decoded.getpixel((0, 0)), (255, 0, 0))


class StillCameraTests(TestCase):
    def test_get_jpg_uses_latest_frame_and_keeps_square_padding(self):
        frame = np.zeros((2, 3, 3), dtype=np.uint8)
        frame[:, :] = [10, 20, 30]

        class FakeVideoCamera:
            cap = SimpleNamespace(isOpened=lambda: True)

            def __init__(self, src=0, **resolution):
                self.src = src
                self.resolution = resolution
                self.stopped = False

            def is_opened(self):
                return True

            def get_frame(self):
                return frame.copy()

            def stop(self):
                self.stopped = True

        with patch("checker.applications.get_img.VideoCamera", FakeVideoCamera):
            camera = StillCamera(src=0, width=3, height=2)
            captured = camera.get_jpg()

        self.assertEqual(captured.shape, (3, 3, 3))
        self.assertTrue((captured[:2, :3] == [10, 20, 30]).all())
        self.assertTrue((captured[2, :3] == [1, 1, 1]).all())


class PlcResultSignalTests(TestCase):
    def _result_signal(self):
        return {
            "complete": {"area": "W", "word_address": 200, "bit": 0},
            "ok": {"area": "W", "word_address": 200, "bit": 1},
            "error": {"area": "W", "word_address": 200, "bit": 2},
        }

    def _client(self):
        class FakeClient:
            def __init__(self):
                self.writes = []
                self.closed = False

            def write_bit(self, area, word_address, bit, value):
                self.writes.append((area, word_address, bit, value))

            def close(self):
                self.closed = True

        return FakeClient()

    def test_true_snap_result_sets_ok_and_clears_error(self):
        client = self._client()

        plc_monitor.write_completed_result_signals(client, self._result_signal(), True)

        self.assertEqual(client.writes, [
            ("W", 200, 1, 1),
            ("W", 200, 2, 0),
            ("W", 200, 0, 0),
        ])

    def test_false_snap_result_sets_error_and_clears_ok(self):
        client = self._client()

        plc_monitor.write_completed_result_signals(client, self._result_signal(), False)

        self.assertEqual(client.writes, [
            ("W", 200, 1, 0),
            ("W", 200, 2, 1),
            ("W", 200, 0, 1),
        ])


# run_monitorはExceptionを捕捉してループを継続するため、
# テストからループを抜けるにはBaseException継承が必要
class StopMonitor(BaseException):
    pass


class PlcMonitorTriggerTests(TestCase):
    """run_monitorの起動インターロックと立ち上がりエッジ検知のテスト。"""

    def _config(self):
        return {
            "monitor": {"area": "W", "word_address": 100, "bit": 0, "poll_interval_seconds": 0.0},
            "result_signal": {
                "complete": {"area": "W", "word_address": 200, "bit": 0},
                "ok": {"area": "W", "word_address": 200, "bit": 1},
                "error": {"area": "W", "word_address": 200, "bit": 2},
            },
        }

    def _client(self, trigger_reads):
        class FakeClient:
            def __init__(self):
                self.trigger_reads = list(trigger_reads)
                self.writes = []
                self.bits = {("W", 200, 0): 1, ("W", 200, 1): 0, ("W", 200, 2): 0}
                self.closed = False

            def read_bit(self, area, word_address, bit):
                if (area, word_address, bit) == ("W", 100, 0):
                    if not self.trigger_reads:
                        raise StopMonitor()
                    return bool(self.trigger_reads.pop(0))
                return bool(self.bits.get((area, word_address, bit), 0))

            def write_bit(self, area, word_address, bit, value):
                self.writes.append((area, word_address, bit, value))
                self.bits[(area, word_address, bit)] = int(value)

            def close(self):
                self.closed = True

        return FakeClient()

    def _run_monitor(self, client):
        # NG結果はcomplete=ONに戻るため、複数回のトリガー受付を検証できる
        snap_result = SimpleNamespace(
            result=False,
            result_dict={"part": 0},
            message="NG",
            timestamp="2026-07-14T00:00:00",
            image_bytes=b"png",
        )
        with (
            patch("checker.applications.plc_monitor.load_config", return_value=self._config()),
            patch("checker.applications.plc_monitor.build_plc_client", return_value=client),
            patch("checker.applications.plc_monitor.is_snap_running", return_value=False),
            patch("checker.applications.plc_monitor.run_checker_confirm_api", return_value=snap_result) as confirm_api,
            patch("checker.applications.plc_monitor.notify_checker_status"),
            patch("checker.applications.plc_monitor.time.sleep"),
        ):
            try:
                plc_monitor.run_monitor()
            except StopMonitor:
                pass
        plc_monitor.clear_latest_plc_result()
        return confirm_api

    def test_trigger_on_at_startup_is_ignored_until_off_is_confirmed(self):
        # 起動時にtrigger=ONが残っている場合、OFFを確認してからの立ち上がりだけ実行する
        client = self._client([1, 1, 0, 1])

        confirm_api = self._run_monitor(client)

        self.assertEqual(confirm_api.call_count, 1)

    def test_trigger_level_on_does_not_retrigger(self):
        # ONレベルが続いても、立ち上がりエッジ1回分しか実行しない
        client = self._client([0, 1, 1, 1])

        confirm_api = self._run_monitor(client)

        self.assertEqual(confirm_api.call_count, 1)

    def test_trigger_rising_edges_run_inspection_each_time(self):
        client = self._client([0, 1, 0, 1])

        confirm_api = self._run_monitor(client)

        self.assertEqual(confirm_api.call_count, 2)


class ConfirmApiTests(TestCase):
    def test_plc_monitor_calls_confirm_websocket_api(self):
        class FakeWebSocket:
            def __init__(self):
                self.sent = []
                self.messages = [
                    b"png-bytes",
                    json.dumps({
                        "message": "OK",
                        "timestamp": "2026-06-26T16:31:16",
                        "result_dict": {"part": 1},
                        "result": True,
                    }),
                ]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def send(self, message):
                self.sent.append(json.loads(message))

            def recv(self, timeout=None):
                return self.messages.pop(0)

        fake_websocket = FakeWebSocket()
        config = {
            "checker_api": {
                "confirm_ws_url": "ws://127.0.0.1:8000/checker/ws/confirm/",
                "timeout": 12.0,
            }
        }

        with patch("checker.applications.plc_monitor.websocket_connect", return_value=fake_websocket) as connect:
            result = plc_monitor.run_checker_confirm_api(config)

        connect.assert_called_once_with(
            "ws://127.0.0.1:8000/checker/ws/confirm/",
            open_timeout=12.0,
            close_timeout=12.0,
            max_size=None,
        )
        self.assertEqual(fake_websocket.sent[0]["snap"], "True")
        self.assertEqual(fake_websocket.sent[0]["source"], "plc_monitor")
        self.assertEqual(result.image_bytes, b"png-bytes")
        self.assertEqual(result.result_dict, {"part": 1})
        self.assertTrue(result.result)

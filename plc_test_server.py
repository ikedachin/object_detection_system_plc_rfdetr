import argparse
import html
import re
import sys
from pathlib import Path
from threading import Lock

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parent
DJANGO_ROOT = PROJECT_ROOT / "object_detection_system"
SETTINGS_PATH = PROJECT_ROOT / "settings" / "plc_settings.yaml"

if str(DJANGO_ROOT) not in sys.path:
    sys.path.insert(0, str(DJANGO_ROOT))

from checker.applications.plc_client import PlcClient  # noqa: E402

app = FastAPI(title="Dummy PLC Test Server")
memory_lock = Lock()
memory = {}

# plc.enabled: true のときは実PLCへのブリッジとして動作する（startupで生成）
plc_bridge = None


class BitWrite(BaseModel):
    area: str
    word_address: int
    bit: int
    value: int


class PlcBridge:
    """ビット読み書きをメモリではなく実PLC（FINS/UDP）へ転送するバックエンド。"""

    def __init__(self, connection_config):
        self.connection_config = dict(connection_config)
        # FINS/UDPアクセスを直列化する（同時リクエストでソケットを共有しないため）
        self.lock = Lock()

    def read_bit(self, area, word_address, bit):
        return int(self._with_client(lambda client: client.read_bit(area, word_address, bit)))

    def write_bit(self, area, word_address, bit, value):
        self._with_client(lambda client: client.write_bit(area, word_address, bit, int(value)))
        return 1 if int(value) else 0

    def _with_client(self, operation):
        with self.lock:
            client = PlcClient(self.connection_config).connect()
            try:
                return operation(client)
            finally:
                client.close()


def load_config(path=SETTINGS_PATH):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def is_plc_bridge_enabled(config):
    return bool(config.get("plc", {}).get("enabled", False))


def bit_key(area, word_address, bit):
    return f"{area}{int(word_address)}.{int(bit):02d}"


def configured_signals():
    config = load_config()
    signals = []
    monitor = config.get("monitor", {})
    if monitor:
        signals.append(("trigger", monitor))
    result_signal = config.get("result_signal", {})
    for name in ("complete", "ok", "error"):
        signal = result_signal.get(name)
        if signal:
            signals.append((name, signal))
    return signals


def configured_keys():
    config = load_config()
    monitor = config.get("monitor", {})
    result_signal = config.get("result_signal", {})
    return {
        "trigger": bit_key(monitor["area"], monitor["word_address"], monitor["bit"]) if monitor else None,
        "complete": bit_key(result_signal["complete"]["area"], result_signal["complete"]["word_address"], result_signal["complete"]["bit"]) if result_signal.get("complete") else None,
        "ok": bit_key(result_signal["ok"]["area"], result_signal["ok"]["word_address"], result_signal["ok"]["bit"]) if result_signal.get("ok") else None,
        "error": bit_key(result_signal["error"]["area"], result_signal["error"]["word_address"], result_signal["error"]["bit"]) if result_signal.get("error") else None,
    }


def initial_values():
    keys = configured_keys()
    return {
        keys["trigger"]: 0,
        keys["complete"]: 1,
        keys["ok"]: 0,
        keys["error"]: 0,
    }


def split_key(key):
    match = re.match(r"^([A-Za-z]+)(\d+)\.(\d+)$", key)
    return match.group(1), int(match.group(2)), int(match.group(3))


def _bridge_call(operation):
    try:
        return operation()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"PLCへのアクセスに失敗しました: {exc}") from exc


def read_bit_value(area, word_address, bit):
    if plc_bridge is not None:
        return _bridge_call(lambda: plc_bridge.read_bit(area, word_address, bit))
    ensure_configured_bits()
    key = bit_key(area, word_address, bit)
    with memory_lock:
        return int(memory.get(key, 0))


def write_bit_value(area, word_address, bit, value):
    if plc_bridge is not None:
        return _bridge_call(lambda: plc_bridge.write_bit(area, word_address, bit, value))
    ensure_configured_bits()
    key = bit_key(area, word_address, bit)
    with memory_lock:
        memory[key] = 1 if int(value) else 0
        return memory[key]


def snapshot_bits():
    if plc_bridge is not None:
        bits = {}
        for _, signal in configured_signals():
            key = bit_key(signal["area"], signal["word_address"], signal["bit"])
            bits[key] = _bridge_call(lambda s=signal: plc_bridge.read_bit(s["area"], s["word_address"], s["bit"]))
        return dict(sorted(bits.items()))
    ensure_configured_bits()
    with memory_lock:
        return dict(sorted(memory.items()))


def apply_initial_state():
    values = initial_values()
    reset = {}
    for key, value in values.items():
        if not key:
            continue
        area, word_address, bit = split_key(key)
        reset[key] = write_bit_value(area, word_address, bit, value)
    return reset


def ensure_configured_bits():
    with memory_lock:
        defaults = initial_values()
        for _, signal in configured_signals():
            key = bit_key(signal["area"], signal["word_address"], signal["bit"])
            memory.setdefault(key, defaults.get(key, 0))


@app.on_event("startup")
def startup():
    global plc_bridge
    config = load_config()
    if is_plc_bridge_enabled(config):
        plc_bridge = PlcBridge(config["connection"])
        # ブリッジモードでは設備の現在状態を壊さないよう、起動時にPLCへ書き込まない
        print(
            "PLC bridge mode: bit access is forwarded to the real PLC at "
            f"{config['connection'].get('host')}:{config['connection'].get('port', 9600)}"
        )
    else:
        apply_initial_state()


@app.get("/", response_class=HTMLResponse)
def index():
    rows = []
    bits = snapshot_bits()
    labels = {bit_key(sig["area"], sig["word_address"], sig["bit"]): name for name, sig in configured_signals()}
    trigger_key = configured_keys().get("trigger") or "trigger"
    if plc_bridge is not None:
        mode_label = "実PLCブリッジモード（操作は実PLCへ書き込まれます）"
    else:
        mode_label = "メモリモード（ダミーPLC）"

    for key, value in bits.items():
        label = labels.get(key, "")
        rows.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td><code>{html.escape(key)}</code></td>"
            f"<td><strong>{value}</strong></td>"
            "<td>"
            f"<button onclick=\"writeBit('{html.escape(key)}', 1)\">ON</button>"
            f"<button onclick=\"writeBit('{html.escape(key)}', 0)\">OFF</button>"
            "</td>"
            "</tr>"
        )

    return f"""
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dummy PLC</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; background: #f6f8fb; color: #20242a; }}
    header {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 20px; }}
    table {{ border-collapse: collapse; width: 100%; background: white; }}
    th, td {{ border: 1px solid #d8dee9; padding: 10px; text-align: left; }}
    th {{ background: #e9eef5; }}
    button {{ margin-right: 8px; padding: 6px 12px; border: 1px solid #9aa7b8; background: white; cursor: pointer; }}
    button.primary {{ background: #2563eb; border-color: #2563eb; color: white; }}
    button.danger {{ background: #b91c1c; border-color: #b91c1c; color: white; }}
    .actions {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .mode {{ font-weight: bold; color: {'#b91c1c' if plc_bridge is not None else '#2563eb'}; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Dummy PLC Test Server</h1>
      <p>PLC監視スクリプトのテスト用メモリです。</p>
      <p class="mode">{html.escape(mode_label)}</p>
    </div>
    <div class="actions">
      <button class="primary" onclick="setTrigger()">{html.escape(trigger_key)} Trigger ON</button>
      <button onclick="resetResults()">Result Reset</button>
      <button class="danger" onclick="clearAll()">All OFF</button>
      <button onclick="location.reload()">Reload</button>
    </div>
  </header>
  <table>
    <thead><tr><th>用途</th><th>ビット</th><th>値</th><th>操作</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <script>
    function splitKey(key) {{
      const match = key.match(/^([A-Za-z]+)(\\d+)\\.(\\d+)$/);
      return {{ area: match[1], word_address: Number(match[2]), bit: Number(match[3]) }};
    }}
    async function writeBit(key, value) {{
      const bit = splitKey(key);
      await fetch('/api/bit', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ ...bit, value }})
      }});
      location.reload();
    }}
    async function setTrigger() {{
      const response = await fetch('/api/trigger', {{ method: 'POST' }});
      if (!response.ok) {{
        const data = await response.json();
        alert(data.detail || 'Trigger is not allowed.');
      }}
      location.reload();
    }}
    async function resetResults() {{
      await fetch('/api/reset-results', {{ method: 'POST' }});
      location.reload();
    }}
    async function clearAll() {{
      await fetch('/api/clear-all', {{ method: 'POST' }});
      location.reload();
    }}
  </script>
</body>
</html>
"""


@app.get("/api/bits")
def get_bits():
    return {"bits": snapshot_bits()}


@app.get("/api/bit/{area}/{word_address}/{bit}")
def get_bit(area: str, word_address: int, bit: int):
    key = bit_key(area, word_address, bit)
    return {"key": key, "value": read_bit_value(area, word_address, bit)}


@app.post("/api/bit")
def set_bit(payload: BitWrite):
    key = bit_key(payload.area, payload.word_address, payload.bit)
    value = write_bit_value(payload.area, payload.word_address, payload.bit, payload.value)
    return {"key": key, "value": value}


@app.post("/api/trigger")
def set_trigger():
    config = load_config()
    monitor = config["monitor"]
    result_signal = config.get("result_signal", {})
    complete = result_signal.get("complete")

    trigger_is_off = read_bit_value(monitor["area"], monitor["word_address"], monitor["bit"]) == 0
    complete_is_on = read_bit_value(complete["area"], complete["word_address"], complete["bit"]) == 1 if complete else True
    if not (trigger_is_off and complete_is_on):
        raise HTTPException(
            status_code=409,
            detail="trigger is allowed only when trigger is OFF and complete is ON",
        )
    value = write_bit_value(monitor["area"], monitor["word_address"], monitor["bit"], 1)
    return {"key": bit_key(monitor["area"], monitor["word_address"], monitor["bit"]), "value": value}


@app.post("/api/reset-results")
def reset_results():
    reset = apply_initial_state()
    return {"reset": reset}


@app.post("/api/clear-all")
def clear_all():
    if plc_bridge is not None:
        bits = {}
        for _, signal in configured_signals():
            key = bit_key(signal["area"], signal["word_address"], signal["bit"])
            bits[key] = write_bit_value(signal["area"], signal["word_address"], signal["bit"], 0)
        return {"bits": dict(sorted(bits.items()))}
    ensure_configured_bits()
    with memory_lock:
        for key in list(memory):
            memory[key] = 0
        return {"bits": dict(sorted(memory.items()))}


def main():
    config = load_config()
    server = config.get("test_server", {})
    uvicorn.run(
        "plc_test_server:app",
        host=server.get("host", "127.0.0.1"),
        port=int(server.get("port", 8010)),
        reload=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run dummy PLC test server.")
    parser.parse_args()
    main()

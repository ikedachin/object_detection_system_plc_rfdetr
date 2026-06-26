import io
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import numpy as np
from asgiref.sync import async_to_sync
from django.test import Client, TestCase, override_settings
from PIL import Image

from checker.applications.detect import detect_objects
from checker.applications import plc_monitor
from checker import checker_consumers
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


class PlcResultSignalTests(TestCase):
    def _config(self):
        return {
            "result_signal": {
                "complete": {"area": "D", "word_address": 200, "bit": 0},
                "ok": {"area": "D", "word_address": 200, "bit": 1},
                "error": {"area": "D", "word_address": 200, "bit": 2},
            }
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

        with patch("checker.applications.plc_monitor.build_plc_client", return_value=client):
            plc_monitor.write_snap_result_signals(SimpleNamespace(result=True), config=self._config())

        self.assertEqual(client.writes, [
            ("D", 200, 1, 1),
            ("D", 200, 2, 0),
            ("D", 200, 0, 0),
        ])
        self.assertTrue(client.closed)

    def test_false_snap_result_sets_error_and_clears_ok(self):
        client = self._client()

        with patch("checker.applications.plc_monitor.build_plc_client", return_value=client):
            plc_monitor.write_snap_result_signals(SimpleNamespace(result=False), config=self._config())

        self.assertEqual(client.writes, [
            ("D", 200, 1, 0),
            ("D", 200, 2, 1),
            ("D", 200, 0, 1),
        ])
        self.assertTrue(client.closed)


class ConfirmApiTests(TestCase):
    def test_confirm_api_writes_plc_signals_by_default(self):
        snap_result = SimpleNamespace(result=True)

        with (
            patch("checker.checker_consumers.run_snap_backend", new=AsyncMock(return_value=snap_result)),
            patch("checker.applications.plc_monitor.write_snap_result_signals") as write_signals,
        ):
            result = checker_consumers.run_confirm_snap_request_sync()

        self.assertIs(result, snap_result)
        write_signals.assert_called_once_with(snap_result)

    def test_confirm_api_can_skip_plc_signal_write_for_plc_monitor_post_processing(self):
        snap_result = SimpleNamespace(result=True)

        with (
            patch("checker.checker_consumers.run_snap_backend", new=AsyncMock(return_value=snap_result)),
            patch("checker.applications.plc_monitor.write_snap_result_signals") as write_signals,
        ):
            result = checker_consumers.run_confirm_snap_request_sync(write_plc_signals=False)

        self.assertIs(result, snap_result)
        write_signals.assert_not_called()

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

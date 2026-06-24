import io
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from asgiref.sync import async_to_sync
from django.test import Client, TestCase
from PIL import Image

from checker.applications.detect import detect_objects
from checker.applications import plc_monitor
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

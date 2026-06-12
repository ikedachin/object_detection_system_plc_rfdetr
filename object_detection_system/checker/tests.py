import numpy as np
from asgiref.sync import async_to_sync
from django.test import TestCase
from PIL import Image

from checker.applications.detect import detect_objects


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

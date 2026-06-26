from unittest.mock import patch

import numpy as np
from django.test import TestCase

from get_imgs.applications import camera_get_data


class DummyThread:
    def __init__(self, target, daemon=False):
        self.target = target
        self.daemon = daemon

    def start(self):
        pass

    def is_alive(self):
        return False

    def join(self, timeout=None):
        pass


class FakeCapture:
    def __init__(self, frame=None):
        self.frame = frame if frame is not None else np.zeros((2, 3, 3), dtype=np.uint8)
        self.opened = True
        self.released = False
        self.props = {}

    def isOpened(self):
        return self.opened

    def read(self):
        return True, self.frame.copy()

    def set(self, prop, value):
        self.props[prop] = value
        return True

    def get(self, prop):
        return self.props.get(prop, 0)

    def release(self):
        self.released = True
        self.opened = False


class VideoCameraTests(TestCase):
    def _patch_camera(self, frame=None):
        fake_capture = FakeCapture(frame=frame)
        return (
            fake_capture,
            patch("get_imgs.applications.camera_get_data.cv2.VideoCapture", return_value=fake_capture),
            patch("get_imgs.applications.camera_get_data.Thread", DummyThread),
            patch("get_imgs.applications.camera_get_data.platform.system", return_value="Linux"),
        )

    def test_video_camera_accepts_width_height_resolution(self):
        fake_capture, video_capture_patch, thread_patch, platform_patch = self._patch_camera()

        with video_capture_patch, thread_patch, platform_patch:
            camera = camera_get_data.VideoCamera(
                src=0,
                width=800,
                height=600,
                startup_delay=0,
                warmup_frames=1,
            )
            try:
                self.assertEqual(camera.width, 800)
                self.assertEqual(camera.height, 600)
                self.assertEqual(camera.image_size, {"width": 800, "height": 600})
                self.assertEqual(fake_capture.props[camera_get_data.cv2.CAP_PROP_FRAME_WIDTH], 800)
                self.assertEqual(fake_capture.props[camera_get_data.cv2.CAP_PROP_FRAME_HEIGHT], 600)
            finally:
                camera.stop()

    def test_video_camera_accepts_image_size_dict_resolution(self):
        _, video_capture_patch, thread_patch, platform_patch = self._patch_camera()

        with video_capture_patch, thread_patch, platform_patch:
            camera = camera_get_data.VideoCamera(
                src=0,
                image_size_dict={"width": 1280, "height": 720},
                startup_delay=0,
                warmup_frames=1,
            )
            try:
                self.assertEqual(camera.width, 1280)
                self.assertEqual(camera.height, 720)
                self.assertEqual(camera.image_size, {"width": 1280, "height": 720})
            finally:
                camera.stop()

    def test_get_frame_returns_copy_of_latest_frame(self):
        frame = np.zeros((2, 3, 3), dtype=np.uint8)
        frame[0, 0] = [10, 20, 30]
        _, video_capture_patch, thread_patch, platform_patch = self._patch_camera(frame=frame)

        with video_capture_patch, thread_patch, platform_patch:
            camera = camera_get_data.VideoCamera(
                src=0,
                width=3,
                height=2,
                startup_delay=0,
                warmup_frames=1,
            )
            try:
                captured = camera.get_frame()
                captured[0, 0] = [99, 99, 99]

                self.assertEqual(camera.get_frame()[0, 0].tolist(), [10, 20, 30])
            finally:
                camera.stop()

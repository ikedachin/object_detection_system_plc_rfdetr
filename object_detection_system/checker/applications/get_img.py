import numpy as np

from get_imgs.applications.camera_get_data import VideoCamera


class StillCamera:
    """
    A class to handle still image capture from a camera using RF-DETR
    Attributes:
        src (int): Camera source index.
        resolution (dict): Camera resolution settings.
        frame (np.ndarray): Current frame captured from the camera.
    """
    def __init__(self, src=0, **resolution):
        self.resolution = resolution
        self.src = src
        self.video_camera = VideoCamera(src=self.src, **self.resolution)
        self.frame = None

    @property
    def cap(self):
        return self.video_camera.cap if self.video_camera is not None else None

    def stop(self):
        """Release the camera device."""
        if self.video_camera is not None:
            try:
                self.video_camera.stop()
            except Exception:
                pass
        self.video_camera = None

    def __del__(self):
        # Best-effort cleanup
        try:
            self.stop()
        except Exception:
            pass

    def get_jpg(self) -> np.ndarray | None:
        if self.video_camera is None or not self.video_camera.is_opened():
            return None

        try:
            self.frame = self.video_camera.get_frame()
            if self.frame is None:
                return None
            # 正方形にする
            h, w = self.frame.shape[:2]
            square_size = max(h, w)
            canvas = np.ones((square_size, square_size, 3), dtype=np.uint8)
            canvas[:h, :w, :] = self.frame
            return canvas
        except Exception:
            print('読み取りエラー')
            return None


# def img2byte(img: np.ndarray) -> bytes:
#     """
#     Convert an image to bytes.
#     :param img: numpy.ndarray, the image to convert
#     :return: bytes, the image in bytes format
#     """
#     ret, buf = cv2.imencode('.png', img, [cv2.IMWRITE_PNG_COMPRESSION, 9])

#     if ret:
#         return buf.tobytes() if ret else b''
#     else:

#         return b''

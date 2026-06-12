import os
import time

import cv2
import numpy as np

class StillCamera:
    """
    A class to handle still image capture from a camera using RF-DETR
    Attributes:
        src (int): Camera source index.
        resolution (dict): Camera resolution settings.
        cap (cv2.VideoCapture): OpenCV VideoCapture object.
        frame (np.ndarray): Current frame captured from the camera.
    """
    def __init__(self, src=0, **resolution):
        self.resolution = resolution
        self.src = src
        self.cap = self._setting_camera(self.src, **self.resolution)
        self.frame = None

    def stop(self):
        """Release the camera device."""
        cap = getattr(self, 'cap', None)
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
        self.cap = None

    def __del__(self):
        # Best-effort cleanup
        try:
            self.stop()
        except Exception:
            pass
    
    def _setting_camera(self, src, **resolution):
        print('Capture Size: ', resolution['width'], resolution['height'])
        # 写真を撮影するためにカメラと接続する
        cap = cv2.VideoCapture(src)
        # カメラ解像度の設定
        if resolution:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution['width'])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution['height'])
        return cap

    def get_jpg(self) -> np.ndarray | None:
        if self.cap is None or not self.cap.isOpened():
            return None
        self.frame = None

        while True:
            try:
                _, self.frame = self.cap.read()
                if self.frame is None:
                    return None
                # 正方形にする
                h, w = self.frame.shape[:2]
                square_size = max(h, w)
                canvas = np.ones((square_size, square_size, 3), dtype=np.uint8)
                canvas[:h, :w, :] = self.frame
                return canvas
            except:
                print('読み取りエラー')
            finally:
                time.sleep(0.5)        


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

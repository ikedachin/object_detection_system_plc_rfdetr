import platform
import time
from threading import Lock, Thread

import cv2


#################################
# Webカメラの解像度1080pを設定
# 内臓カメラは720pを除外するため
WEB_COM_HEIGHT = 1080
WEB_COM_WIDTH = 1920

USE_INTERNAL_CAMERA = False  # 内臓カメラを使用するかどうか（Windows機のみ）
#################################


def find_available_cameras():
    """利用可能なカメラのインデックスを検索"""
    print("カメラ検索をスキップ中（デバッグモード）...")
    
    # デバッグ用：カメラ検索をスキップしてデフォルトカメラを返す
    available_cameras = [0]  # デフォルトカメラ
    print(f"デフォルトカメラを使用: {available_cameras}")
    return available_cameras


# 画素数でカメラの番号を取得
available_cameras = find_available_cameras()

class VideoCamera:
    """
    別スレッドで常時キャプチャし、最新フレームを保持する。
    """
    def __init__(self, src=None, **resolution):
        image_size = resolution.get('image_size_dict') or {}
        self.width = int(resolution.get('width') or image_size.get('width') or 640)
        self.height = int(resolution.get('height') or image_size.get('height') or 480)
        self.image_size = {'width': self.width, 'height': self.height}

        self.fps = self._resolve_positive_number(resolution.get('fps'), 30)
        default_sec_per_frame = 1 / self.fps if self.fps > 0 else 1 / 30
        self.sec_per_frame = self._resolve_positive_number(
            resolution.get('sec_per_frame'),
            default_sec_per_frame,
        )
        self.warmup_frames = int(resolution.get('warmup_frames', 5))
        self.startup_delay = self._resolve_positive_number(resolution.get('startup_delay'), 0.5, allow_zero=True)
        print('Capture Size: ', self.width, self.height)
        print(resolution)

        if src is None:
            cameras = find_available_cameras()
            if not cameras:
                raise RuntimeError("利用可能なカメラが見つかりません")
            src = cameras[0]
            print(f"カメラ {src} を使用します")

        self.src = src
        self.cap = None
        self.lock = Lock()
        self.frame = None
        self.running = False
        self.thread = None

        self._initialize_camera()
        self.running = True
        self.thread = Thread(target=self._update, daemon=True)
        self.thread.start()

        if self.startup_delay:
            time.sleep(self.startup_delay)

    @staticmethod
    def _resolve_positive_number(value, default, allow_zero=False):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if number > 0 or (allow_zero and number == 0):
            return number
        return default

    def _camera_backends(self):
        if platform.system() == 'Windows':
            print('Windows の場合、DirectShow / MSMF / 既定バックエンドを順に試します')
            return [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        print('MacOS または Linux の場合、デフォルトのバックエンドを使用します')
        return [None]

    def _open_capture(self, backend):
        if backend is None:
            return cv2.VideoCapture(self.src)
        return cv2.VideoCapture(self.src, backend)

    def _configure_capture(self, cap):
        for prop, value in (
            (cv2.CAP_PROP_FRAME_WIDTH, self.width),
            (cv2.CAP_PROP_FRAME_HEIGHT, self.height),
            (cv2.CAP_PROP_FPS, self.fps),
            (cv2.CAP_PROP_BUFFERSIZE, 1),
        ):
            try:
                cap.set(prop, value)
            except Exception as exc:
                print(f"カメラ設定を適用できませんでした: prop={prop}, value={value}, error={exc}")

        try:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        except Exception as exc:
            print(f"MJPG FourCC を適用できませんでした: {exc}")

    def _warm_up_capture(self, cap):
        warmup_frames = max(1, self.warmup_frames)
        last_frame = None
        for _ in range(warmup_frames):
            ret, frame = cap.read()
            if ret and frame is not None:
                last_frame = frame.copy()
        if last_frame is not None:
            with self.lock:
                self.frame = last_frame
            return True
        return False

    def _initialize_camera(self):
        """カメラを初期化"""
        print(f"カメラ {self.src} を初期化中...")
        previous_cap = self.cap
        self.cap = None
        if previous_cap is not None:
            try:
                previous_cap.release()
            except Exception:
                pass

        for backend in self._camera_backends():
            cap = None
            try:
                cap = self._open_capture(backend)
                if not cap.isOpened():
                    print(f"カメラ {self.src} を開けません (バックエンド: {backend})")
                    continue

                self._configure_capture(cap)
                if not self._warm_up_capture(cap):
                    print(f"カメラ {self.src} からフレームを読み込めません (バックエンド: {backend})")
                    continue

                self.cap = cap
                print(f"カメラ {self.src} が正常に初期化されました (バックエンド: {backend})")
                break
            except Exception as e:
                print(f"カメラ初期化エラー (バックエンド: {backend}): {e}")
            finally:
                if self.cap is not cap and cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass

        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError(f"カメラ {self.src} を初期化できません")

        # 実際に設定された解像度を確認
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f'実際のキャプチャサイズ: {actual_width}x{actual_height}')

    def _update(self):
        frame_count = 0
        error_count = 0
        max_errors = 10  # 最大エラー回数
        
        while self.running:
            try:
                if self.cap is None or not self.cap.isOpened():
                    print("カメラが閉じられています。再初期化を試行...")
                    self._initialize_camera()
                    continue
                
                ret, frame = self.cap.read()
                if not ret:
                    error_count += 1
                    print(f"フレーム読み込み失敗 ({error_count}/{max_errors})")
                    
                    if error_count >= max_errors:
                        print("最大エラー回数に達しました。カメラを再初期化します...")
                        self.cap.release()
                        self.cap = None
                        error_count = 0
                        time.sleep(1)
                        continue
                    
                    time.sleep(0.1)
                    continue
                
                # 成功した場合はエラーカウントをリセット
                error_count = 0
                frame_count += 1

                with self.lock:
                    self.frame = frame.copy()

                # # 100フレームごとにメッセージ表示
                # if frame_count % 100 == 0:
                #     print(f"フレーム {frame_count} を処理しました")
                # print(f"フレーム {frame_count} を取得しました (サイズ: {self.frame.shape})")
            except Exception as e:
                error_count += 1
                print(f"フレーム処理エラー: {e} ({error_count}/{max_errors})")
                
                if error_count >= max_errors:
                    print("最大エラー回数に達しました。カメラを停止します...")
                    break
                
            time.sleep(self.sec_per_frame)
        
        print("カメラ更新スレッドが終了しました")

    def get_jpeg(self) -> bytes:
        """現在のフレームをJPEG形式で取得"""
        try:
            with self.lock:
                frm = self.frame.copy() if self.frame is not None else None
            
            if frm is None:
                return b''
            
            # JPEG品質を80に設定してエンコード
            ret, buf = cv2.imencode('.jpg', frm, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return buf.tobytes() if ret else b''
            
        except Exception as e:
            print(f"JPEG エンコードエラー: {e}")
            return b''

    def get_frame(self):
        """現在のフレームを取得（デバッグ用）"""
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def is_opened(self):
        """カメラが開いているかチェック"""
        return self.cap is not None and self.cap.isOpened()

    def stop(self):
        """カメラを停止"""
        print("カメラを停止中...")
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
        if self.cap:
            self.cap.release()
            self.cap = None
        print("カメラが停止されました")



# カメラのテスト用関数
def test_camera():
    """カメラのテスト"""
    try:
        print("カメラテストを開始...")
        available_cameras = find_available_cameras()
        
        if not available_cameras:
            print("利用可能なカメラが見つかりません")
            return False
        
        print(f"テスト用にカメラ {available_cameras[0]} を使用")
        camera = VideoCamera(available_cameras[0], width=640, height=480)
        
        # 数秒間テスト
        for i in range(5):
            frame_data = camera.get_jpeg()
            if frame_data:
                print(f"テスト {i+1}/5: フレーム取得成功 ({len(frame_data)} bytes)")
            else:
                print(f"テスト {i+1}/5: フレーム取得失敗")
            time.sleep(1)
        
        camera.stop()
        print("カメラテスト完了")
        return True
        
    except Exception as e:
        print(f"カメラテストエラー: {e}")
        return False

# 使用例:
# available_cameras = find_available_cameras()
# if available_cameras:
#     camera = VideoCamera(available_cameras[0], width=640, height=480)
#     print("カメラが正常に初期化されました")
# else:
#     print("利用可能なカメラが見つかりません")

# テスト実行:
if __name__ == "__main__":
    print('__file__:', __file__)
    print('available_cameras:', available_cameras)

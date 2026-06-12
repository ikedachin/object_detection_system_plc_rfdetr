import cv2
from threading import Thread, Lock
import time
import platform


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
        self.image_size = resolution['image_size_dict']
        self.width = self.image_size.get('width', 640)
        self.height = self.image_size.get('height', 480)

        self.fps = resolution.get('fps', 30)
        self.sec_per_frame = resolution.get('sec_per_frame', 1)
        print('Capture Size: ', self.width, self.height)
        print(resolution)
        
        # カメラインデックスが指定されていない場合、利用可能なカメラを検索
        # if src is None:
        #     available_cameras = find_available_cameras()
        #     if not available_cameras:
        #         raise RuntimeError("利用可能なカメラが見つかりません")
        #     src = available_cameras[0]
        #     print(f"カメラ {src} を使用します")
        
        self.src = src
        self.cap = None
        self._initialize_camera()
        
        self.lock = Lock()
        self.frame = None
        self.running = True
        Thread(target=self._update, daemon=True).start()
        
        # カメラの初期化を待つ
        time.sleep(0.5)
    
    def _initialize_camera(self):
        """カメラを初期化"""
        print(f"カメラ {self.src} を初期化中...")
        self.cap = None
        # DirectShowバックエンドを試行（Windowsの場合）
        if platform.system() == 'Windows':
            print('Windows の場合、DirectShow バックエンドを使用します')
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
            for backend in backends:
                try:
                    self.cap = cv2.VideoCapture(self.src, backend)
                    if self.cap.isOpened():
                        # テスト読み込み
                        ret, test_frame = self.cap.read()
                        if ret:
                            print(f"カメラ {self.src} が正常に初期化されました (バックエンド: {backend})")
                            break
                        else:
                            print(f"カメラ {self.src} からフレームを読み込めません (バックエンド: {backend})")
                            self.cap.release()
                            self.cap = None
                    else:
                        print(f"カメラ {self.src} を開けません (バックエンド: {backend})")
                        if self.cap:
                            self.cap.release()
                            self.cap = None
                except Exception as e:
                    print(f"カメラ初期化エラー (バックエンド: {backend}): {e}")
                    if self.cap:
                        self.cap.release()
                        self.cap = None
        else:
            print('MacOS または Linux の場合、デフォルトのバックエンドを使用します')
            self.cap = cv2.VideoCapture(self.src)
        
        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError(f"カメラ {self.src} を初期化できません")
        
        # 解像度を設定
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        # バッファサイズを設定（遅延を減らすため）
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
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
                    self.frame = frame
                    del frame
                
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
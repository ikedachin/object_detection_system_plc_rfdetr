# can用　HD対応
import asyncio
import copy
import datetime
import gc
import json
import os
import time
from pathlib import Path
from django.conf import settings

from channels.generic.websocket import AsyncWebsocketConsumer
from get_imgs.applications.camera_get_data import VideoCamera, available_cameras



#############################################################
######################### globals ###########################
#############################################################
NOW = datetime.datetime.now()
FRAME_STILL = None

# print("in get_imgs consumers.py; ", os.getcwd())
# yamlファイルは使用せず、Webインターフェースからの設定のみを使用

# デフォルト設定（Webインターフェースで変更可能）
FPS = 30
SEC_INTERVAL_TO_SAVE = 60  # 60秒ごとに画像を保存
SEC_PER_FRAME = 1 / FPS
image_size = 'SD480p'  # デフォルト画像サイズ
# print(f'Default settings - FPS: {FPS}, SEC_PER_FRAME: {SEC_PER_FRAME}, Interval: {SEC_INTERVAL_TO_SAVE}s')

# folders設定（デフォルト）
folders = {
    'auto': {
        'path': '../data_collection/',
        'extension': '.png'  # デフォルトの拡張子をpngに変更
    }
}

#############################################################
# 画像の解像度設定（Webインターフェースで変更可能）
#############################################################
image_size_dict = {
    'HD1080p': {'width': 1920, 'height': 1080},
    'HD720p': {'width': 1280, 'height': 720},
    'SD480p': {'width': 640, 'height': 480},
    'SD360p': {'width': 480, 'height': 360},
}

#############################################################

class Checker(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(json.dumps({
            'message': 'Connected to the get_imgs WebSocket',
            'timestamp': datetime.datetime.now().isoformat()
        }))

    async def disconnect(self, close_code):
        await self.close()

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Process the received data
        global timestamp
        timestamp = datetime.datetime.now().isoformat()
        response = {
            'message': f'Received: {data}',
            'timestamp': timestamp
        }
        await self.send(json.dumps(response))





class ServerTime(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.send_task = asyncio.create_task(self.send_time())

    async def disconnect(self, close_code):
        self.send_task.cancel()

    async def send_time(self):
        # print("ServerTime connected, starting to send time updates...")
        while True:
            global NOW
            NOW = datetime.datetime.now()
            send_dict = {
                'now_time': NOW.strftime('%H:%M:%S')
            }

            # 仮に安定したら止めるロジックも入れられる
            await self.send(text_data=json.dumps(send_dict))
            await asyncio.sleep(1)  # 1秒おきに送信  




class CameraConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # print(f"Camera WebSocket接続要求: {self.scope['client']} -> {self.scope['path']}")
        await self.accept()
        self.send_task = None
        self.camera = None
        self.image_size = None
        self.project_name = None
        self.send_error_count = 0
        
        # FPS設定をインスタンス変数として初期化
        self.fps = FPS
        self.sec_per_frame = SEC_PER_FRAME
        self.sec_interval_to_save = SEC_INTERVAL_TO_SAVE
        # カメラの初期化
        self.available_cameras = available_cameras
        
        print(f"Camera WebSocket接続確立: {self.channel_name} (初期FPS: {self.fps})")
        await self.send(json.dumps({
            'message': 'Camera WebSocketに接続されました (設定待機中)',
            'timestamp': NOW.isoformat(),
            'channel': self.channel_name,
            'initial_fps': self.fps
        }))

    async def disconnect(self, code):
        # コルーチンを止める
        if self.send_task:
            self.send_task.cancel()
            try:
                await self.send_task
            except asyncio.CancelledError:
                pass
            finally:
                self.send_task = None
        if self.camera:
            try:
                self.camera.stop()
            finally:
                self.camera = None
            print("Camera stopped.")

    async def _stop_running_camera(self):
        """既存の送信タスクとカメラを確実に停止する（設定再適用・切断の両方で利用）"""
        if self.send_task and not self.send_task.done():
            self.send_task.cancel()
            try:
                await self.send_task
            except asyncio.CancelledError:
                pass
            finally:
                self.send_task = None

        if self.camera:
            try:
                self.camera.stop()
            except Exception:
                pass
            finally:
                self.camera = None

    async def receive(self, text_data=None, bytes_data=None):
        # 設定反映ボタン押下後にクライアントから設定が送られてくる想定
        if text_data:
            try:
                data = json.loads(text_data)
                print(f"Received camera settings: {data}")

                # 設定再適用時のリーク防止: まず既存タスク/カメラを停止
                await self._stop_running_camera()
                
                # インスタンス変数として設定を保存（グローバル変数の問題を回避）
                self.image_size = data.get('image_size', image_size)
                received_fps = data.get('fps', str(FPS))
                received_interval = data.get('interval', str(SEC_INTERVAL_TO_SAVE))
                self.project_name = data.get('project_name', '')
                
                # プロジェクト名が空の場合はデフォルトを使用
                if not self.project_name:
                    now = datetime.datetime.now()
                    self.project_name = f"project_{now.strftime('%Y%m%d_%H%M%S')}"
                
                print(f"Received settings from web interface - Image size: {self.image_size}, FPS: {received_fps}, Interval: {received_interval}, Project: {self.project_name}")
                # カメラインスタンスを立てる

                # インスタンス変数として設定を保存
                try:
                    # FPS設定の更新
                    if received_fps and float(received_fps) > 0:
                        self.fps = int(float(received_fps))
                        self.sec_per_frame = 1 / self.fps
                        print(f"✅ FPS updated to: {self.fps} (SEC_PER_FRAME: {self.sec_per_frame:.4f}s)")
                    else:
                        print(f"⚠️ Invalid FPS value received: {received_fps}, using default: {FPS}")
                        self.fps = FPS
                        self.sec_per_frame = SEC_PER_FRAME
                    
                    # 保存間隔設定の更新
                    if received_interval and float(received_interval) > 0:
                        self.sec_interval_to_save = int(float(received_interval))
                        print(f"✅ Save interval updated to: {self.sec_interval_to_save}s")
                    else:
                        print(f"⚠️ Invalid interval value received: {received_interval}, using default: {SEC_INTERVAL_TO_SAVE}")
                        self.sec_interval_to_save = SEC_INTERVAL_TO_SAVE

                    resolution = {
                        "image_size_dict": image_size_dict[self.image_size],
                        "fps": self.fps,
                        "sec_per_frame": self.sec_per_frame,
                    }

                    if self.available_cameras:
                        self.camera = VideoCamera(src=self.available_cameras[0], **resolution)
                    else:
                        raise ValueError("No available cameras found")
                    print(f"📊 Current settings - FPS: {self.fps}, Frame interval: {self.sec_per_frame:.4f}s, Save interval: {self.sec_interval_to_save}s")
                    
                except (ValueError, ZeroDivisionError) as e:
                    print(f"❌ Error updating settings: {e}")
                    print(f"🔄 Fallback to safe defaults - FPS: 30, Interval: 60s")
                    self.fps = 30
                    self.sec_per_frame = 1 / 30
                    self.sec_interval_to_save = 60
                
                # 新しいカメラタスクを開始
                self.send_task = asyncio.create_task(self.send_frames())
                await self.send(json.dumps({
                    'message': f'Camera started with resolution: {image_size_dict[self.image_size]}, FPS: {self.fps}, Save interval: {self.sec_interval_to_save}s (Settings applied from web interface)',
                    'timestamp': NOW.isoformat()
                }))
            except Exception as e:
                print(f"Error processing camera settings: {e}")
                await self.send(json.dumps({
                    'error': f'Settings processing error: {str(e)}',
                    'timestamp': NOW.isoformat()
                }))

    async def send_frames(self):
        """
        設定したfps JPEG バイト列を binary メッセージとして送信
        """
        try:
            print(f"カメラを開始します - 解像度: {image_size_dict[self.image_size]}")
            
            # カメラの初期化を試行
            camera_initialized = False
            max_init_attempts = 3
            
            for attempt in range(max_init_attempts):
                try:
                    print(f"カメラ初期化試行 {attempt + 1}/{max_init_attempts}")
                    print(f"解像度設定: {image_size_dict[self.image_size]}")
                    # self.camera = VideoCamera(src=None, **image_size_dict[self.image_size])  # srcをNoneにして自動検索
                    # self.camera = VideoCamera(src=0, **image_size_dict[self.image_size])  # srcをNoneにして自動検索
                    camera_initialized = True
                    print("✅ カメラが正常に初期化されました")
                    break
                except Exception as e:
                    print(f"❌ カメラ初期化試行 {attempt + 1} 失敗: {e}")
                    import traceback
                    traceback.print_exc()
                    if self.camera:
                        try:
                            self.camera.stop()
                        except:
                            pass
                        self.camera = None
                    
                    if attempt < max_init_attempts - 1:
                        print("⏰ 2秒後に再試行します...")
                        await asyncio.sleep(2)
            
            if not camera_initialized:
                error_msg = "カメラの初期化に失敗しました。以下を確認してください:\n1. カメラが接続されているか\n2. 他のアプリケーションがカメラを使用していないか\n3. カメラのドライバが正常にインストールされているか"
                print(error_msg)
                await self.send(json.dumps({
                    'error': error_msg,
                    'timestamp': NOW.isoformat()
                }))
                return
            
            # カメラの初期化を少し待つ
            await asyncio.sleep(1)
            
            start_time = time.time()
            frame_count = 0
            no_frame_count = 0
            max_no_frame = 30  # 30回連続でフレームが取得できない場合は停止
            last_save_time = time.time()  # 最後に保存した時間を記録
            
            print(f"フレーム送信ループ開始 - プロジェクト: {self.project_name}, 保存間隔: {self.sec_interval_to_save}秒, FPS: {self.fps}")
            
            await self.send(json.dumps({
                'message': 'カメラが正常に開始されました',
                'project_name': self.project_name,
                'image_size': self.image_size,
                'fps': self.fps,
                'save_interval': self.sec_interval_to_save,
                'save_path': str(get_project_data_collection_path(self.project_name)),
                'timestamp': NOW.isoformat()
            }))
            
            while True:
                if not self.camera or not self.camera.is_opened():
                    print("カメラが利用できません")
                    break
                
                frame = self.camera.get_jpeg()   # 同期関数なのでスレッドで回っても OK
                if not frame:
                    no_frame_count += 1
                    print(f"フレーム取得失敗 {no_frame_count}/{max_no_frame}")
                    
                    if no_frame_count >= max_no_frame:
                        print("フレーム取得の失敗が続いています。カメラを停止します。")
                        await self.send(json.dumps({
                            'error': 'カメラからフレームを取得できません',
                            'timestamp': NOW.isoformat()
                        }))
                        break
                    
                    await asyncio.sleep(0.1)
                    continue
                
                # フレーム取得成功
                no_frame_count = 0
                frame_count += 1
                
                # デバッグ: フレームサイズとFPS設定を確認
                # if frame_count % 50 == 0:  # 50フレームごとにログ出力
                #     print(f"フレーム {frame_count}: {len(frame)} bytes, FPS: {self.fps}, 間隔: {self.sec_per_frame:.4f}s, WebSocket状態: {self.channel_name if hasattr(self, 'channel_name') else 'unknown'}")
                    
                global FRAME_STILL
                del FRAME_STILL
                gc.collect()  # メモリを解放
                FRAME_STILL = copy.deepcopy(frame)  # 画像を保存しておく

                # 画像をWebSocketで送信
                try:
                    # WebSocket接続が生きているかチェック
                    if hasattr(self, 'channel_layer') and hasattr(self, 'channel_name'):
                        await self.send(bytes_data=frame)
                        # if frame_count % 50 == 0:
                        #     print(f"✅ フレーム {frame_count} をWebSocketで送信完了 (チャンネル: {self.channel_name}, {len(frame)} bytes)")
                        # 送信エラーカウントをリセット
                        self.send_error_count = 0
                    else:
                        print("❌ WebSocket接続が無効です")
                        break
                        
                except Exception as send_error:
                    print(f"❌ WebSocket送信エラー (フレーム {frame_count}): {send_error}")
                    import traceback
                    traceback.print_exc()
                    
                    # 送信エラーが続く場合は接続を切断
                    if hasattr(self, 'send_error_count'):
                        self.send_error_count += 1
                    else:
                        self.send_error_count = 1
                    
                    if self.send_error_count >= 10:
                        print("❌ WebSocket送信エラーが続いています。接続を終了します。")
                        break
                
                # 自動保存の間隔チェック
                current_time = time.time()
                if current_time - last_save_time >= self.sec_interval_to_save: # 指定の時間ごとに更新
                    last_save_time = current_time
                    # print(f"自動保存タイミング到達 (経過: {current_time - start_time:.1f}秒, 間隔: {self.sec_interval_to_save}秒)")
                    
                    # プロジェクト名に基づく正しい保存パス
                    try:
                        auto_save_dir = get_project_data_collection_path(self.project_name)
                        now_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                        output_path = auto_save_dir / f"snap_{now_str}.jpg"
                        # print(f"自動保存開始: {output_path} (フレーム{frame_count})")
                        
                        with open(output_path, "wb") as image_file:
                            image_file.write(frame)
                        
                        # ファイルサイズを確認
                        file_size = output_path.stat().st_size
                        print(f"✅ 自動保存完了（Auto）: {output_path} ({file_size} bytes)")
                        
                    except Exception as e:
                        print(f"❌ 自動保存エラー: {e}")
                        import traceback
                        traceback.print_exc()
                        
                        # フォールバック保存先
                        fallback_dir = Path(settings.BASE_DIR.parent) / 'data_collection_fallback'
                        fallback_dir.mkdir(parents=True, exist_ok=True)
                        fallback_path = fallback_dir / f"snap_{now_str}.jpg"
                        try:
                            with open(fallback_path, "wb") as image_file:
                                image_file.write(frame)
                            print(f"✅ フォールバック保存完了: {fallback_path}")
                        except Exception as fe:
                            print(f"❌ フォールバック保存もエラー: {fe}")
                        
                del frame
                gc.collect()  # メモリを解放
                await asyncio.sleep(self.sec_per_frame)  # インスタンス変数を使用

        except asyncio.CancelledError:
            # disconnect() 等でキャンセルされる想定。finallyで解放して上位に伝播。
            raise
        except Exception as e:
            error_msg = f"カメラエラー: {e}"
            print(error_msg)
            await self.send(json.dumps({
                'error': error_msg,
                'details': 'カメラの接続を確認してください。他のアプリケーションがカメラを使用している可能性があります。',
                'timestamp': NOW.isoformat()
            }))
        finally:
            if self.camera:
                try:
                    self.camera.stop()
                finally:
                    self.camera = None
                print("カメラが停止されました")





class Snap(AsyncWebsocketConsumer):
    """スナップショット撮影用WebSocketConsumer - 修正版"""
    async def connect(self):
        await self.accept()
        self.project_name = None
        self.received_settings = False
        # print("Snap WebSocket connected, waiting for settings...")

    async def disconnect(self, close_code):
        # print("Snap WebSocket disconnected")
        await self.close()

    async def receive(self, text_data=None, bytes_data=None):
        if text_data and not self.received_settings:
            try:
                # 最初のメッセージでプロジェクト名などを受信
                msg = json.loads(text_data)
                self.project_name = msg.get('project_name')
                if not self.project_name:
                    # フォールバック: 日付時刻で生成
                    now = datetime.datetime.now()
                    self.project_name = f"project_{now.strftime('%Y%m%d_%H%M%S')}"
                
                self.received_settings = True
                # print(f"Snap project name set to: {self.project_name}")
                
                # 保存先パスを作成（正しいプロジェクトフォルダ）
                self.base_dir = get_project_data_collection_path(self.project_name)
                # print(f"Snap保存先ディレクトリ: {self.base_dir}")
                
                # FRAME_STILLがあれば画像を送信
                await self.send_snapshot()
                
            except Exception as e:
                print(f"Error processing snap settings: {e}")
                await self.send(json.dumps({
                    'error': f'Settings processing error: {str(e)}',
                    'timestamp': NOW.isoformat()
                }))

    async def send_snapshot(self):
        global FRAME_STILL
        if FRAME_STILL is not None:
            try:
                # 保存先をmanualに変更 → プロジェクト直下に保存
                output_path = self.base_dir / f"snap_{NOW.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
                with open(output_path, "wb") as image_file:
                    image_file.write(FRAME_STILL)
                file_size = output_path.stat().st_size
                print(f"✅ 手動保存完了（Snap）: {output_path} ({file_size} bytes)")
                # クライアントに画像を送信
                await self.send(bytes_data=FRAME_STILL)
                
                # メモリクリーンアップ
                del FRAME_STILL
                gc.collect()
                FRAME_STILL = None
                
            except Exception as e:
                print(f"Error saving snapshot: {e}")
                await self.send(json.dumps({
                    'error': f'Snapshot save error: {str(e)}',
                    'timestamp': NOW.isoformat()
                }))
        else:
            print("No image available to send.")
            await self.send(json.dumps({
                'message': 'No image available',
                'timestamp': NOW.isoformat()
            }))
        
        await self.disconnect(1000)  # 正常終了で接続を切断

#############################################################
######################### Helper Functions #################
#############################################################

def get_project_data_collection_path(project_name):
    """プロジェクトのdata_collectionフォルダパスを取得"""
    if not project_name:
        # プロジェクト名がない場合のフォールバック
        project_name = f"default_project_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # プロジェクトベースディレクトリ: BASE_DIR.parent/projects/project_name/data_collection
    base_dir = settings.BASE_DIR.parent  # inventry_checkerディレクトリ
    project_path = base_dir / 'projects' / project_name / 'data_collection'
    
    # ディレクトリが存在しない場合は作成
    project_path.mkdir(parents=True, exist_ok=True)
    
    # print(f"プロジェクト保存パス: {project_path}")
    return project_path

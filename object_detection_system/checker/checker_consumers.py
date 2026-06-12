# can用　HD対応
import asyncio
import datetime
import json

from channels.layers import get_channel_layer
from channels.generic.websocket import AsyncWebsocketConsumer
from checker.applications.snap_service import (
    ensure_camera_initialized,
    run_snap_backend,
    snap_result_to_json,
    stop_camera_if_running,
)

#############################################################
######################### globals ###########################
#############################################################
NOW = datetime.datetime.now()
FRAME_STILL = None


#############################################################
class CheckerServerTime(AsyncWebsocketConsumer):
    async def connect(self):
        ensure_camera_initialized()
        await self.accept()
        await self.channel_layer.group_add("checker_status", self.channel_name)
        self.send_task = asyncio.create_task(self.send_time())

    async def disconnect(self, close_code):
        if hasattr(self, 'send_task') and self.send_task:
            self.send_task.cancel()
            try:
                await self.send_task
            except asyncio.CancelledError:
                pass
        await self.channel_layer.group_discard("checker_status", self.channel_name)
        stop_camera_if_running()

    async def send_time(self):
        # print("ServerTime connected, starting to send time updates...")
        while True:
            global NOW
            NOW = datetime.datetime.now()
            send_dict = {
                'now_time': NOW.strftime('%H:%M:%S')
            }

            # 仮に安定したら止めるロジックも入れられる
            # print('checker consumers.py: ServerTime connected, sending time updates...')
            await self.send(text_data=json.dumps(send_dict))
            await asyncio.sleep(1)  # 1秒おきに送信  

    async def send_checker_status(self, event):
        await self.send(text_data=json.dumps(event["payload"]))


#############################################################
class Confirm(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print('=== WebSocket Confirm connected ===')
        print(f'Channel name: {self.channel_name}')
        print('Waiting for snapshot confirmation...')

    async def receive(self, text_data=None, bytes_data=None):
        """
        クライアントからのメッセージを受信した時の処理
        """
        print('=== WebSocket message received ===')
        print(f'Text data: {text_data}')
        print(f'Bytes data: {bytes_data}')
        print('Starting inference...')

        try:
            snap_result = await run_snap_backend()
            await self.send(bytes_data=snap_result.image_bytes)
            await self.send(text_data=snap_result_to_json(snap_result))
        except Exception as e:
            import traceback
            traceback.print_exc()
            await self.send(text_data=json.dumps({
                'error': str(e),
                'timestamp': NOW.isoformat()
            }))
        
        # 推論完了後に接続を切断
        await self.disconnect(1000)
    
    async def disconnect(self, close_code):
        print(f'=== WebSocket Confirm disconnected ===')
        print(f'Close code: {close_code}')
        # print("Camera disconnected")
        await self.close()



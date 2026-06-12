from channels.generic.websocket import AsyncWebsocketConsumer
import json

class RfdetrTrainingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('rfdetr_training', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('rfdetr_training', self.channel_name)

    async def send_metrics(self, event):
        await self.send(text_data=json.dumps({
            'epoch': event.get('epoch'),
            'total_epochs': event.get('total_epochs'),
            'metrics': event.get('metrics'),
            'status': event.get('status', 'running'),
        }))

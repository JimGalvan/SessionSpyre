import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import UserSession

class SessionConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f"session_{self.session_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        events = text_data_json['events']
        user_id = text_data_json['user_id']

        session, created = await sync_to_async(UserSession.objects.get_or_create)(
            session_id=self.session_id,
            defaults={'user_id': user_id, 'events': events}
        )
        if not created:
            session.events.extend(events)
            await sync_to_async(session.save)()

        await self.send(text_data=json.dumps({'status': 'success'}))
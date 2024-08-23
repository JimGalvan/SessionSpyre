import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import UserSession


class SessionConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f"session_{self.session_id}"

        # Join the session group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Mark the session as live
        await self.set_session_live_status(True)

        await self.accept()

        # Notify live status change if applicable
        await self.notify_live_status(True)

    async def disconnect(self, close_code):
        # Leave the session group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        # Mark the session as not live
        await self.set_session_live_status(False)

        # Notify live status change if applicable
        await self.notify_live_status(False)

    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        events = text_data_json['events']
        user_id = text_data_json['user_id']

        # Update or create the session
        session, created = await sync_to_async(UserSession.objects.get_or_create)(
            session_id=self.session_id,
            defaults={'user_id': user_id, 'events': events}
        )
        if not created:
            session.events.extend(events)
            await sync_to_async(session.save)()

        await self.send(text_data=json.dumps({'status': 'success'}))

    async def set_session_live_status(self, is_live):
        """Set the live status of the session."""
        await sync_to_async(UserSession.objects.filter(session_id=self.session_id).update)(live=is_live)

    async def notify_live_status(self, is_live):
        """Notify about the session's live status via another WebSocket."""
        await self.channel_layer.group_send(
            "live_status",
            {
                "type": "live_status_update",
                "session_id": self.session_id,
                "live": is_live
            }
        )


class LiveStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join the live_status group
        await self.channel_layer.group_add(
            "live_status",  # Group name must match the one used in SessionConsumer
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave the live_status group
        await self.channel_layer.group_discard(
            "live_status",
            self.channel_name
        )

    async def live_status_update(self, event):
        # Handle the message sent from SessionConsumer
        session_id = event['session_id']
        live = event['live']

        # Send the live status update to the WebSocket client
        await self.send(text_data=json.dumps({
            'session_id': session_id,
            'live': live
        }))

import json
import logging

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import UserSession

logger = logging.getLogger(__name__)


class SessionConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.group_name = None
        self.session_id = None
        self.live_session_group_postfix = "live_session"

    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f"session_{self.session_id}"

        # Logging connection attempt
        logger.info(f"SessionConsumer: Connecting to session {self.session_id}")

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

        # Notify the frontend about the new session creation
        await self.notify_session_creation()

    async def disconnect(self, close_code):
        # Logging disconnection
        logger.info(f"SessionConsumer: Disconnecting from session {self.session_id} with close code {close_code}")

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
        logger.info(f"SessionConsumer: Received data in session {self.session_id}")

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

        logger.info(f"SessionConsumer: Sending live session event for session {self.session_id}")

        await self.channel_layer.group_send(
            f"{self.group_name}_{self.live_session_group_postfix}",
            {
                "type": "live_session_event",
                "text": json.dumps(events[-1])  # Send the last event
            }
        )

        await self.send(text_data=json.dumps({'status': 'success'}))

    async def set_session_live_status(self, is_live):
        logger.info(f"SessionConsumer: Setting live status to {is_live} for session {self.session_id}")
        await sync_to_async(UserSession.objects.filter(session_id=self.session_id).update)(live=is_live)

    async def notify_live_status(self, is_live):
        logger.info(f"SessionConsumer: Notifying live status change to {is_live} for session {self.session_id}")
        await self.channel_layer.group_send(
            "live_status",
            {
                "type": "live_status_update",
                "session_id": self.session_id,
                "live": is_live
            }
        )

    async def notify_session_creation(self):
        """Notify the session updates group about the creation of a new session."""
        logger.info(f"SessionConsumer: Notifying about new session creation for session {self.session_id}")
        await self.channel_layer.group_send(
            "session_updates",
            {
                "type": "session_created",
                "session_id": self.session_id
            }
        )


class SessionUpdatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("SessionUpdatesConsumer: Connecting to session updates")

        await self.channel_layer.group_add(
            "session_updates",
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        logger.info(f"SessionUpdatesConsumer: Disconnecting from session updates with close code {close_code}")

        await self.channel_layer.group_discard(
            "session_updates",
            self.channel_name
        )

    async def session_created(self, event):
        logger.info(f"SessionUpdatesConsumer: New session created with session_id {event['session_id']}")

        await self.send(text_data=json.dumps({
            'action': 'session-created',
            'session_id': event['session_id']
        }))


class LiveStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("LiveStatusConsumer: Connecting to live status updates")

        await self.channel_layer.group_add(
            "live_status",  # Group name must match the one used in SessionConsumer
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        logger.info(f"LiveStatusConsumer: Disconnecting from live status updates with close code {close_code}")

        await self.channel_layer.group_discard(
            "live_status",
            self.channel_name
        )

    async def live_status_update(self, event):
        logger.info(
            f"LiveStatusConsumer: Received live status update for session {event['session_id']} with status {event['live']}")

        session_id = event['session_id']
        live = event['live']

        await self.send(text_data=json.dumps({
            'session_id': session_id,
            'live': live
        }))


class LiveSessionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f"session_{self.session_id}"
        self.group_postfix: str = "live_session"

        logger.info(f"LiveSessionConsumer: Connecting to live session {self.session_id}")

        # Join the session group
        await self.channel_layer.group_add(
            f"{self.group_name}_{self.group_postfix}",
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        logger.info(
            f"LiveSessionConsumer: Disconnecting from live session {self.session_id} with close code {close_code}")

        # Leave the session group
        await self.channel_layer.group_discard(
            self.group_name + self.group_postfix,
            self.channel_name
        )

    async def live_session_event(self, event):
        """Handle the live session event."""
        logger.info(f"LiveSessionConsumer: Received live session event for session {self.session_id}")
        logger.debug(f"Event data: {event}")

        await self.send(text_data=event['text'])

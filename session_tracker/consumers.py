import json
import logging
import uuid
from datetime import datetime, timedelta
from urllib.parse import parse_qs

import pytz
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import UserSession, Site, UserAccount
from .utils.session_utils import validate_site_key, get_exclusion_rules, is_ip_excluded, \
    is_domain_or_subdomain_excluded, is_session_id_valid, is_url_pattern_excluded, get_client_ip

logger = logging.getLogger(__name__)


class SessionConsumer(AsyncWebsocketConsumer):
    SESSION_TIMEOUT = 30  # Timeout in minutes for the session

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ip_address = None
        self.exclusion_rules = None
        self.user_id = None
        self.site_url = None
        self.site_id = None
        self.connection_closed = None
        self.site_key = None
        self.group_name = None
        self.session_id = None

    async def connect(self):
        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        self.site_key = query_params.get('siteKey', [None])[0]
        self.site_id = query_params.get('siteId', [None])[0]
        self.session_id = query_params.get('sessionId', [None])[0]
        self.site_url = query_params.get('siteUrl', [None])[0]
        self.user_id = query_params.get('userId', [None])[0]
        self.ip_address = get_client_ip(self)


        logger.debug(
            f"SessionConsumer: Received query params - siteKey: {self.site_key}, siteId: {self.site_id}, sessionId: {self.session_id}, siteUrl: {self.site_url}")

        # **Site Key Validation**
        site = await validate_site_key(self.site_id, self.site_key)
        if not site:
            logger.error(f"SessionConsumer: Invalid site key {self.site_key}. Disconnecting.")
            await self.close(code=4004)
            return

        if not self.user_id:
            logger.error(f"SessionConsumer: User ID is required. Disconnecting.")
            await self.close(code=4004)
            return

        # Validate URL exclusion rules
        user = await UserAccount.objects.filter(id=self.user_id).afirst()
        self.exclusion_rules = await get_exclusion_rules(user.id, self.site_id)

        # Check if the current IP should be excluded from recording
        if await is_ip_excluded(self.ip_address, self.exclusion_rules):
            logger.info(f"SessionConsumer: IP {self.ip_address} is excluded from tracking.")
            await self.close(code=4004)
            return

        # Check if the current URL should be excluded from recording
        if await is_domain_or_subdomain_excluded(self.site_url, self.exclusion_rules):
            logger.info(f"SessionConsumer: URL {self.scope['path']} is excluded from tracking.")
            await self.close(code=4004)
            return

        # Validate session ID
        if not await is_session_id_valid(self.session_id, self.site_id):
            self.session_id = str(uuid.uuid4())

        self.group_name = f"session_{self.session_id}"

        logger.info(f"SessionConsumer: Connecting to session {self.session_id}")

        # Join the session group
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.notify_live_status(True)
        await self.notify_session_creation()

        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'session_id',
            'message': self.session_id
        }))

    async def disconnect(self, close_code):
        logger.info(f"SessionConsumer: Disconnecting from session {self.session_id} with close code {close_code}")

        # Leave the session group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        await self.set_session_live_status(False)
        await self.notify_live_status(False)

        self.connection_closed = True  # Set the flag to True

    async def receive(self, text_data=None, bytes_data=None):
        logger.info(f"SessionConsumer: Received data in session {self.session_id}")

        text_data_json = json.loads(text_data)
        events = text_data_json.get('events')
        user_id = text_data_json.get('user_id')
        site_id = text_data_json.get('site_id')

        if self.exclusion_rules:
            # Check if the current URL should be excluded from recording
            if await is_url_pattern_excluded(self.site_url, self.exclusion_rules):
                logger.info(f"SessionConsumer: URL {self.scope['path']} is excluded from tracking.")
                await self.send(text_data=json.dumps({'status': 'error', 'message': 'URL is excluded from tracking'}))
                return

        try:
            site = await sync_to_async(Site.objects.get)(id=site_id)
        except Site.DoesNotExist:
            logger.error(f"SessionConsumer: Site with id {site_id} does not exist.")
            await self.send(text_data=json.dumps({'status': 'error', 'message': 'Site does not exist'}))
            return

        # Check if the session already exists
        try:
            session = await sync_to_async(UserSession.objects.get)(id=self.session_id, site=site)
            session.live = True
            await sync_to_async(session.save)()
            create_session = False
        except UserSession.DoesNotExist:
            session = None
            create_session = True

        if create_session:
            await self.create_new_session(events, site, user_id)

        else:
            # Check if the session has been inactive for more than the threshold
            updated_at_aware = session.updated_at.astimezone(pytz.UTC)
            current_time_utc = datetime.now(pytz.UTC)
            is_session_inactive = current_time_utc - updated_at_aware > timedelta(minutes=self.SESSION_TIMEOUT)

            if is_session_inactive:
                # Mark the current session as ended
                session.live = False
                await sync_to_async(session.save)()

                # Notify about the session ending
                await self.notify_live_status(False)

                logger.info(f"SessionConsumer: Session {self.session_id} ended due to inactivity.")

                # Create a new session
                await self.create_new_session(events, site, user_id)

            else:
                # If the session is still active, continue recording events
                session.events.extend(events)
                await sync_to_async(session.save)()

        await self.notify_live_status(True)

        # Send the event to all live session viewers
        await self.channel_layer.group_send(
            # f"{self.group_name}_{self.live_session_group_postfix}",
            f"{self.group_name}",
            {
                "type": "live_session_event",
                "text": json.dumps(events[-1])  # Send the last event
            }
        )

        await self.send(text_data=json.dumps({'status': 'success'}))

    async def live_session_event(self, event):
        """Handle the live session event."""
        logger.info(f"LiveSessionConsumer: Received live session event for session {self.session_id}")
        logger.debug(f"Event data: {event}")

        await self.send(text_data=event['text'])

    async def create_new_session(self, events, site, user_id, session_id=None):
        session = await sync_to_async(UserSession.objects.create)(
            id=self.session_id,
            session_id=self.session_id,
            site=site,
            user_id=user_id,
            events=events,
            live=True
        )

        logger.info(f"SessionConsumer: New session {self.session_id} started.")

    async def set_session_live_status(self, is_live):
        logger.info(f"SessionConsumer: Setting live status to {is_live} for session {self.session_id}")
        await sync_to_async(UserSession.objects.filter(id=self.session_id).update)(live=is_live)

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
            f"LiveSessionConsumer: Disconnecting from live session {self.session_id} with close code {close_code}"
        )

        # Correctly format the group name with the underscore between group_name and group_postfix
        await self.channel_layer.group_discard(
            f"{self.group_name}_{self.group_postfix}",
            self.channel_name
        )



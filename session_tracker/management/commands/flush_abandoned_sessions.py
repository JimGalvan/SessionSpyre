import asyncio
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from session_tracker.models import UserSession
from session_tracker.services import RedisSessionService, S3SessionService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Flush abandoned Redis sessions to PostgreSQL before TTL expiry'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ttl-threshold',
            type=int,
            default=3600,
            help='Flush sessions with TTL below this value in seconds (default: 3600)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be flushed without actually flushing'
        )

    def handle(self, *args, **options):
        if not getattr(settings, 'USE_REDIS_SESSION_BUFFER', False):
            self.stdout.write('Redis session buffer is disabled. Nothing to do.')
            return

        ttl_threshold = options['ttl_threshold']
        dry_run = options['dry_run']

        flushed, errors = asyncio.run(self.flush_sessions(ttl_threshold, dry_run))

        if dry_run:
            self.stdout.write(f'Would flush {flushed} sessions')
        else:
            self.stdout.write(self.style.SUCCESS(f'Flushed {flushed} sessions, {errors} errors'))

    async def flush_sessions(self, ttl_threshold: int, dry_run: bool) -> tuple[int, int]:
        redis_service = RedisSessionService()
        session_ids = await redis_service.get_all_session_ids()

        flushed = 0
        errors = 0

        for session_id in session_ids:
            try:
                ttl = await redis_service.get_ttl(session_id)

                if ttl == -2:
                    continue

                if ttl != -1 and ttl < ttl_threshold:
                    if dry_run:
                        events_count = await redis_service.get_events_count(session_id)
                        self.stdout.write(f'  Would flush session {session_id} (TTL: {ttl}s, events: {events_count})')
                        flushed += 1
                        continue

                    events = await redis_service.get_events(session_id)
                    if not events:
                        await redis_service.delete_session(session_id)
                        continue

                    try:
                        session = await UserSession.objects.filter(id=session_id).afirst()
                        if session:
                            use_s3 = getattr(settings, 'USE_S3_SESSION_ARCHIVE', False)
                            if use_s3:
                                s3_service = S3SessionService()
                                s3_key = s3_service.upload_session(
                                    str(session.id), str(session.site_id), events
                                )
                                session.events_s3_key = s3_key
                                session.events_count = len(events)
                                session.archived = True
                                session.events = None
                                logger.info(f'Archived abandoned session {session_id} to S3 ({len(events)} events)')
                            else:
                                session.events = events
                                session.events_count = len(events)
                                logger.info(f'Flushed abandoned session {session_id} ({len(events)} events)')

                            session.live = False
                            await session.asave()
                            await redis_service.delete_session(session_id)
                            flushed += 1
                        else:
                            await redis_service.delete_session(session_id)
                            logger.warning(f'Orphaned Redis session {session_id} deleted (no PostgreSQL record)')
                    except Exception as e:
                        errors += 1
                        logger.error(f'Failed to flush session {session_id}: {e}')

            except Exception as e:
                errors += 1
                logger.error(f'Error processing session {session_id}: {e}')

        return flushed, errors

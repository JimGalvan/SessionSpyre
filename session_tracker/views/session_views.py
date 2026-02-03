import json
from datetime import datetime
from datetime import timedelta

import pytz
from asgiref.sync import async_to_sync
from django.conf import settings
from django.shortcuts import render

from session_tracker.models import UserSession, Site
from session_tracker.services import RedisSessionService, S3SessionService


def sessions_view(request, site_id):
    user_id: str = request.user.id
    site: Site = Site.objects.get(id=site_id)
    today_date = datetime.now().date()
    sessions: list = UserSession.objects.filter(user_id=user_id, site=site, created_at__date=today_date)
    return render(request, 'sessions/sessions.html', {'site': site, 'sessions': sessions, 'today_date': today_date})


def replay_session(request, session_id):
    session: UserSession = UserSession.objects.get(id=session_id)

    events_json = None

    if getattr(settings, 'USE_REDIS_SESSION_BUFFER', False) and session.live:
        redis_service = RedisSessionService()
        events = async_to_sync(redis_service.get_events)(str(session.id))
        if events:
            events_json = json.dumps(events)

    if not events_json and session.archived and session.events_s3_key:
        s3_service = S3SessionService()
        events = s3_service.download_session(session.events_s3_key)
        events_json = json.dumps(events)

    if not events_json:
        events_json = session.get_events_json

    return render(request, 'sessions/session_player.html', {
        'session': session,
        'events_json': events_json
    })


def delete_session(request, session_id):
    session: UserSession = UserSession.objects.get(id=session_id)
    session.delete()
    user_id: str = request.user.id
    sessions: list = UserSession.objects.filter(user_id=user_id)
    return render(request, 'sessions/session_list.html', {'sessions': sessions})


def sessions_list(request, site_id):
    user_id = request.user.id
    date_str = request.GET.get('date')
    today_date = datetime.now().date()

    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        sessions = UserSession.objects.filter(user_id=user_id, site_id=site_id, created_at__date=selected_date)
    else:
        sessions = UserSession.objects.filter(user_id=user_id, site_id=site_id, created_at__date=today_date)

    check_live_status(sessions)
    return render(request, 'sessions/session_list.html', {'sessions': sessions, 'today_date': today_date})


def check_live_status(sessions):
    # using the datetime field updated_at which is UTC datetime, if the last updated_at is more than 1 minute ago
    # then the session is not live
    for session in sessions:
        if session.updated_at < datetime.now(pytz.UTC) - timedelta(minutes=1):
            session.live = False
            session.save()

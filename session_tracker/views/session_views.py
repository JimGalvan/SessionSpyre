from datetime import timedelta, datetime

import pytz
from django.shortcuts import render

from session_tracker.models import UserSession, Site


def sessions_view(request, site_id):
    user_id: str = request.user.id
    site: Site = Site.objects.get(id=site_id)
    sessions: list = UserSession.objects.filter(user_id=user_id, site=site)
    return render(request, 'sessions/sessions.html', {'site': site, 'sessions': sessions})


def replay_session(request, session_id):
    session: UserSession = UserSession.objects.get(session_id=session_id)
    return render(request, 'sessions/session_player.html', {'session': session})


def delete_session(request, session_id):
    session: UserSession = UserSession.objects.get(session_id=session_id)
    session.delete()
    user_id: str = request.user.id
    sessions: list = UserSession.objects.filter(user_id=user_id)
    return render(request, 'sessions/session_list.html', {'sessions': sessions})


def sessions_list(request, site_id):
    user_id: str = request.user.id
    sessions: list = UserSession.objects.filter(user_id=user_id, site_id=site_id)
    check_live_status(sessions)
    return render(request, 'sessions/session_list.html', {'sessions': sessions})


def check_live_status(sessions):
    # using the datetime field updated_at which is UTC datetime, if the last updated_at is more than 1 minute ago
    # then the session is not live
    for session in sessions:
        if session.updated_at < datetime.now(pytz.UTC) - timedelta(minutes=1):
            session.live = False
            session.save()

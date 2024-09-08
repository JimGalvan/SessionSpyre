import uuid
from datetime import datetime

from django.core.paginator import Paginator
from django.shortcuts import render

from session_tracker.models import UserSession

dummy_sessions = [
    UserSession(session_id=str(uuid.uuid4()), created_at=datetime.now(), live=True),
    UserSession(session_id=str(uuid.uuid4()), created_at=datetime.now(), live=False),
    UserSession(session_id=str(uuid.uuid4()), created_at=datetime.now(), live=True),
    UserSession(session_id=str(uuid.uuid4()), created_at=datetime.now(), live=True),
    UserSession(session_id=str(uuid.uuid4()), created_at=datetime.now(), live=False),
    UserSession(session_id=str(uuid.uuid4()), created_at=datetime.now(), live=True),
]


def sessions_view(request):
    paginator = Paginator(dummy_sessions, 4)  # Show 5 sessions per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'sessions/sessions.html', {'sessions': dummy_sessions})


def sessions_list(request):
    paginator = Paginator(dummy_sessions, 4)  # Show 5 sessions per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'sessions/session_list.html', {'sessions': dummy_sessions})

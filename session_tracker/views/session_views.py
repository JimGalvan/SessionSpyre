from django.shortcuts import render

from session_tracker.models import UserSession


def sessions_view(request):
    user_id: str = request.user.id
    sessions: list = UserSession.objects.filter(user_id=user_id)
    return render(request, 'sessions.html', {'sessions': sessions})


def replay_session(request, session_id):
    session: UserSession = UserSession.objects.get(session_id=session_id)
    return render(request, 'session_player.html', {'session': session})


def delete_session(request, session_id):
    session: UserSession = UserSession.objects.get(session_id=session_id)
    session.delete()
    user_id: str = request.user.id
    sessions: list = UserSession.objects.filter(user_id=user_id)
    return render(request, 'session_list.html', {'sessions': sessions})


def sessions_list(request):
    user_id: str = request.user.id
    sessions: list = UserSession.objects.filter(user_id=user_id)
    return render(request, 'session_list.html', {'sessions': sessions})

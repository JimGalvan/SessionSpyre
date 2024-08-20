from django.shortcuts import render

from SessionSpyre.models import UserSession


def sessions_view(request):
    user_id: str = request.user.id
    sessions: list = UserSession.objects.filter(user_id=user_id).order_by('-created_at')
    return render(request, 'sessions.html', {'sessions': sessions})


def replay_session(request, session_id):
    session = UserSession.objects.get(session_id=session_id)
    return render(request, 'replay_session.html', {'session': session})

from django.shortcuts import render

from SessionSpyre.models import UserSession


def sessions_view(request):
    user_tz: str = request.user.userprofile.timezone
    user_id: str = request.user.id
    sessions: list = UserSession.objects.filter(user_id=user_id).order_by('-created_at')
    return render(request, 'sessions.html', {'sessions': sessions, 'user_tz': user_tz})


def replay_session(request, session_id):
    session: UserSession = UserSession.objects.get(session_id=session_id)
    return render(request, 'replay_session.html', {'session': session})


def delete_session(request, session_id):
    user_tz: str = request.user.userprofile.timezone
    session: UserSession = UserSession.objects.get(session_id=session_id)
    session.delete()
    user_id: str = request.user.id
    sessions: list = UserSession.objects.filter(user_id=user_id).order_by('-created_at')
    return render(request, 'partials/sessions_table.html', {'sessions': sessions, 'user_tz': user_tz})

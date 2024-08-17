from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ninja import NinjaAPI

from .models import UserSession

api = NinjaAPI()


@api.post("/save-session/")
@csrf_exempt  # Apply if CSRF protection is not needed
def save_session(request, payload: dict):
    session, created = UserSession.objects.get_or_create(
        session_id=payload['session_id'],
        defaults={'user_id': payload['user_id'], 'events': payload['events']}
    )
    if not created:
        session.events.extend(payload['events'])
        session.save()
    return {"status": "success"}


@api.get("/replay-session/{session_id}")
def replay_session(request, session_id: str):
    session = UserSession.objects.get(session_id=session_id)
    return JsonResponse({"events": session.events})

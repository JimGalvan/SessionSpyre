from django.http import JsonResponse
from ninja import NinjaAPI, Schema

from .models import UserSession

api = NinjaAPI()


class SessionPayload(Schema):
    session_id: str
    user_id: str
    events: list


@api.post("/save-session/")
def save_session(request, payload: SessionPayload):
    session, created = UserSession.objects.get_or_create(
        session_id=payload.session_id,
        defaults={'user_id': payload.user_id, 'events': payload.events}
    )
    if not created:
        session.events.extend(payload.events)
        session.save()
    return {"status": "success"}

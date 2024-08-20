import json

from django.db import models


class UserSession(models.Model):
    session_id = models.CharField(max_length=255, unique=True)
    user_id = models.CharField(max_length=255)
    events = models.JSONField()  # Stores rrweb events as JSON
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['created_at']),
        ]
        # Optional: If you frequently query a combination of fields, you can create a composite index.
        # models.Index(fields=['user_id', 'created_at']),
        # You can also add db_index=True on individual fields for performance optimization.
        # models.CharField(max_length=255, db_index=True)

    def __str__(self):
        return f"Session {self.session_id} for User {self.user_id}"

    @property
    def get_events_json(self):
        return json.dumps(self.events)

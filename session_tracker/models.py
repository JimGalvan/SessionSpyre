import hashlib
import json
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    timezone = models.CharField(max_length=50, default='UTC')


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.userprofile.save()


def generate_site_key(user_id: int) -> str:
    unique_string = f"{user_id}-{uuid.uuid4()}"
    return hashlib.sha256(unique_string.encode()).hexdigest()


class Site(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sites')
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True, blank=True, null=True)
    key = models.CharField(max_length=64, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def sessions_count(self):
        return self.sessions.count()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = generate_site_key(self.user.id)
        super().save(*args, **kwargs)


class UserSession(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='sessions')
    session_id = models.CharField(max_length=255, unique=True)
    user_id = models.CharField(max_length=255)
    events = models.JSONField()
    live = models.BooleanField(default=False)
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

        ordering = ['-live', '-created_at']

    def __str__(self):
        return f"Session {self.session_id} for User {self.user_id}"

    @property
    def get_events_json(self):
        return json.dumps(self.events)


class URLExclusionRule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    url_pattern = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

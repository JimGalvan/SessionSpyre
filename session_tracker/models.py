import hashlib
import json
import uuid

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserAccount(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Adding related_name to avoid clashes
    groups = models.ManyToManyField(
        Group,
        related_name="useraccount_set",  # Custom related name for groups
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="useraccount_permissions",  # Custom related name for permissions
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE)
    timezone = models.CharField(max_length=50, default='UTC')


@receiver(post_save, sender=UserAccount)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.userprofile.save()


def generate_site_key(user_id: uuid.UUID) -> str:
    unique_string = f"{user_id}-{uuid.uuid4()}"
    return hashlib.sha256(unique_string.encode()).hexdigest()


class Site(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='sites')
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, blank=True, null=True)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
        ordering = ['-live', '-created_at']

    def __str__(self):
        return f"Session {self.session_id} for User {self.user_id}"

    @property
    def get_events_json(self):
        return json.dumps(self.events)


class URLExclusionRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    DOMAIN = 'domain'
    SUBDOMAIN = 'subdomain'
    URL_PATTERN = 'url_pattern'

    EXCLUSION_TYPES = [
        (DOMAIN, 'Domain'),
        (SUBDOMAIN, 'Subdomain'),
        (URL_PATTERN, 'URL Pattern'),
    ]

    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    exclusion_type = models.CharField(max_length=20, choices=EXCLUSION_TYPES, default=URL_PATTERN)
    domain = models.CharField(max_length=255, help_text="Enter the domain or subdomain", blank=True, null=True)
    url_pattern = models.CharField(max_length=255, help_text="Enter the URL pattern (e.g., '/admin/*')", blank=True,
                                   null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.exclusion_type}: {self.domain or ''}{self.url_pattern or ''}"

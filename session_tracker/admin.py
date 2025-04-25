from django.contrib import admin
from .models import UserAccount, UserProfile, Site, UserSession, URLExclusionRule

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'

@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    inlines = [UserProfileInline]

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'user', 'created_at', 'sessions_count')
    search_fields = ('name', 'domain', 'user__username')
    list_filter = ('created_at',)
    readonly_fields = ('key',)

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user_id', 'site', 'live', 'created_at')
    search_fields = ('session_id', 'user_id')
    list_filter = ('live', 'created_at', 'site')
    readonly_fields = ('events', 'get_events_json')

@admin.register(URLExclusionRule)
class URLExclusionRuleAdmin(admin.ModelAdmin):
    list_display = ('exclusion_type', 'domain', 'url_pattern', 'ip_address', 'site', 'user')
    search_fields = ('domain', 'url_pattern', 'ip_address')
    list_filter = ('exclusion_type', 'site')

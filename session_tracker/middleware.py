from django.utils import timezone
from django.http import HttpResponseForbidden
import os


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = request.session.get('django_timezone')
        if tzname:
            timezone.activate(tzname)
        else:
            timezone.deactivate()
        response = self.get_response(request)
        return response


class IPRestrictionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Get the allowed IP from environment variable or use a default for development
        self.allowed_ip = os.environ.get('ALLOWED_IP', None)
        # Flag to enable/disable IP restriction
        self.ip_restriction_enabled = os.environ.get('ENABLE_IP_RESTRICTION', 'False').lower() in ('true', '1', 't')

    def __call__(self, request):
        if self.ip_restriction_enabled and self.allowed_ip:
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                # X-Forwarded-For can be a comma-separated list of IPs.
                # The client's IP is the first one.
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')
            
            # Block requests if IP doesn't match
            if ip != self.allowed_ip:
                return HttpResponseForbidden('Access denied: IP restriction enabled')
        
        response = self.get_response(request)
        return response

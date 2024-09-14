from django.conf import settings


def settings_context_processor(request):
    return {
        'SCRIPT_URL': settings.SCRIPT_URL,
        # Add other settings as needed
    }

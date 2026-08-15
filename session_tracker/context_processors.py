from django.conf import settings


def settings_context_processor(request):
    script_url = settings.SCRIPT_URL
    if script_url and not script_url.startswith(('http://', 'https://')):
        script_url = request.build_absolute_uri(script_url)
    return {
        'SCRIPT_URL': script_url,
        # Add other settings as needed
    }

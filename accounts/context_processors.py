from django.conf import settings


def registration_settings(request):
    return {"registration_enabled": settings.REGISTRATION_ENABLED}

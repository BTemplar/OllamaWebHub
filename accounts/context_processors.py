from typing import Any

from django.conf import settings
from django.http import HttpRequest


def registration_settings(request: HttpRequest) -> dict[str, Any]:
    """
    Expose registration feature flag to templates.

    Args:
        request (HttpRequest): Current HTTP request.

    Returns:
        dict[str, Any]: Template context with ``registration_enabled``.
    """
    return {"registration_enabled": settings.REGISTRATION_ENABLED}

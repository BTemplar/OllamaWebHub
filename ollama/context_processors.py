from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest


def ollama_status(request: HttpRequest) -> dict[str, Any]:
    """
    Provide cached Ollama server availability text for templates.

    Args:
        request (HttpRequest): Current HTTP request.

    Returns:
        dict[str, Any]: Template context with ``ollama_version`` label.
    """
    cache_key = "ollama_version_label"
    version_label = cache.get(cache_key)
    if version_label is None:
        from ollama.ollama_api import get_ollama_client

        version = get_ollama_client().get_version()
        version_label = (
            f"Ollama version: {version}" if version else "Ollama not available!"
        )
        cache.set(cache_key, version_label, settings.OLLAMA_MODELS_CACHE_SECONDS)
    return {"ollama_version": version_label}

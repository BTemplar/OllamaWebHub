from django.apps import AppConfig


class OllamaAppConfig(AppConfig):
    """Django application configuration for the Ollama chat app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ollama"

    def ready(self) -> None:
        """Register signal handlers when the app is loaded."""
        import ollama.signals  # noqa: F401

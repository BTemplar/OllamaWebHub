from django.apps import AppConfig


class OllamaAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ollama'

    def ready(self):
        import ollama.signals  # noqa: F401

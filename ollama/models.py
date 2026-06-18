from django.contrib.auth.models import User
from django.db import models

from ollama.image_processor import chat_message_image_path


class ChatBranch(models.Model):
    """A user-owned chat thread with model and generation settings."""

    class RequestType(models.TextChoices):
        RESPONSE = "RP", "Response"
        CHAT = "CH", "Chat"

    class ResponseType(models.TextChoices):
        STREAM = "ST", "Stream"
        ONETIME = "OT", "One-Time"

    name = models.CharField(max_length=90)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)
    prompt = models.TextField(blank=True, null=True)
    request_type = models.CharField(
        max_length=2,
        choices=RequestType.choices,
        default=RequestType.CHAT,
    )
    response_type = models.CharField(
        max_length=2,
        choices=ResponseType.choices,
        default=ResponseType.STREAM,
    )
    selected_model = models.CharField(max_length=90, default="llama3:latest")
    temperature = models.FloatField(default=0.7)
    multimodal = models.BooleanField(default=False)
    think = models.BooleanField(default=False)
    reasoning = models.BooleanField(default=False)
    num_ctx = models.IntegerField(default=2048)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        """Return the chat branch display name."""
        return self.name


class ChatMessage(models.Model):
    """A single message within a chat branch."""

    class Sender(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    chat_branch = models.ForeignKey(
        ChatBranch, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.CharField(max_length=9, choices=Sender.choices)
    message = models.TextField()
    prompt = models.TextField(blank=True, null=True)
    think = models.TextField(blank=True, default="")
    image = models.ImageField(
        upload_to=chat_message_image_path,
        blank=True,
        null=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["chat_branch", "timestamp"]),
        ]

    def __str__(self) -> str:
        """Return a short description of the message context."""
        return f"Message in {self.chat_branch.name} at {self.timestamp}"

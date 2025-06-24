from django.db import models
from django.contrib.auth.models import User


class ChatBranch(models.Model):
    """
    A model for storing chat branch information.

    Attributes:
        name (str): The name of the chat branch.
        user (User): The user associated with the chat branch.
        description (str): A description of the chat branch.
        prompt (str): The prompt for the chat branch.
        request_type (str): The type of request for the chat branch.
        response_type (str): The type of response for the chat branch.
        selected_model (str): The selected model for the chat branch.
        temperature (float): The temperature for the chat branch.
        multimodal (bool): Whether the chat branch is multimodal.
        think (bool): Whether the chat branch is thinking.
        reasoning (bool): Whether the chat branch is reasoning.
        num_ctx (int): The number of context for the chat branch.
    """

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
        default=ResponseType.ONETIME,
    )
    selected_model = models.CharField(
        max_length=90,
        default="llama3:latest",
    )
    temperature = models.FloatField(default=0.7)
    multimodal = models.BooleanField(default=False)
    think = models.BooleanField(default=False)
    reasoning = models.BooleanField(default=False)
    num_ctx = models.IntegerField(default=2048)

    def __str__(self):
        return self.name


class ChatMessage(models.Model):
    """
    A model for storing chat message information.

    Attributes:
        chat_branch (ChatBranch): The chat branch associated with the chat message.
        sender (str): The sender of the chat message. May have three types: "assistant", "user", "system".
        message (str): The message content.
        prompt (str): The prompt for the chat message.
        think (str): The think for the chat message.
        image_base64 (str): The base64 representation of the image for the chat message.
        timestamp (datetime): The timestamp of the chat message.
    """

    chat_branch = models.ForeignKey(ChatBranch, on_delete=models.CASCADE)
    sender = models.CharField(max_length=9)  # May have three types: "assistant", "user", "system"
    message = models.TextField()
    prompt = models.TextField(blank=True, null=True)
    think = models.TextField()
    image_base64 = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message in {self.chat_branch.name} at {self.timestamp}"
from django.db import models
from django.contrib.auth.models import User

class ChatBranch(models.Model):
    name = models.CharField(max_length=90)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)
    selected_model = models.CharField(max_length=90, default='llama3:latest')
    temperature = models.FloatField(default=0.7)
    multimodal = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class ChatMessage(models.Model):
    chat_branch = models.ForeignKey(ChatBranch, on_delete=models.CASCADE)
    sender = models.CharField(max_length=9) # May have three types: "assistant", "user", "system"
    message = models.TextField()
    image_base64 = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message in {self.chat_branch.name} at {self.timestamp}"
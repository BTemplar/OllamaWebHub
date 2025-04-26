from django.db import models
from django.contrib.auth.models import User

class ChatBranch(models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class ChatMessage(models.Model):
    chat_branch = models.ForeignKey(ChatBranch, on_delete=models.CASCADE)
    sender = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message in {self.chat_branch.name} at {self.timestamp}"
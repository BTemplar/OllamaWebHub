from django.db.models.signals import post_delete
from django.dispatch import receiver

from ollama.image_processor import delete_stored_chat_image
from ollama.models import ChatMessage


@receiver(post_delete, sender=ChatMessage)
def delete_chat_message_image_file(sender, instance, **kwargs):
    if instance.image:
        delete_stored_chat_image(instance.image.name)

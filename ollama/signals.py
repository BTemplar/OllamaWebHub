from typing import Any

from django.db.models.signals import post_delete
from django.dispatch import receiver

from ollama.image_processor import delete_stored_chat_image
from ollama.models import ChatMessage


@receiver(post_delete, sender=ChatMessage)
def delete_chat_message_image_file(
    sender: type[ChatMessage], instance: ChatMessage, **kwargs: Any
) -> None:
    """
    Remove the image file from storage when a chat message is deleted.

    Args:
        sender (type[ChatMessage]): Signal sender model class.
        instance (ChatMessage): Deleted chat message instance.
        **kwargs (Any): Additional signal keyword arguments.
    """
    if instance.image:
        delete_stored_chat_image(instance.image.name)

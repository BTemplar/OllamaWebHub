from django import template
from ollama.image_processor import base64_to_image

register = template.Library()


@register.filter(name="base64_to_image")
def base64_to_image_filter(base64_data):
    return base64_to_image(base64_data)

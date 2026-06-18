import logging

from django.conf import settings
from django.core.cache import cache

from ollama.image_processor import image_field_to_base64
from ollama.models import ChatBranch, ChatMessage
from ollama.ollama_api import get_ollama_client

logger = logging.getLogger(__name__)

PROMPT_PREFIX = (
    "This is a SYSTEM message. NEVER respond to it, it describes your "
    "behavior PATTERN or INSTRUCTIONS that the user wants you to FOLLOW: "
)


def get_available_models():
    cache_key = "ollama_available_models"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    payload = get_ollama_client().list_models()
    models = []
    if payload and isinstance(payload.get("models"), list):
        models = [
            model["name"]
            for model in payload["models"]
            if "embed" not in model.get("name", "")
        ]

    cache.set(cache_key, models, settings.OLLAMA_MODELS_CACHE_SECONDS)
    return models


def _model_base_name(model_name):
    return model_name.split(":", 1)[0].lower()


def _get_model_capability_lists():
    cache_key = "ollama_model_capabilities"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    client = get_ollama_client()
    multimodal = []
    reasoning = []
    seen_multimodal = set()
    seen_reasoning = set()

    for model_name in get_available_models():
        payload = client.show_model(model_name)
        if not payload:
            continue
        capabilities = payload.get("capabilities") or []
        base_name = _model_base_name(model_name)
        if "vision" in capabilities and base_name not in seen_multimodal:
            seen_multimodal.add(base_name)
            multimodal.append(base_name)
        if "thinking" in capabilities and base_name not in seen_reasoning:
            seen_reasoning.add(base_name)
            reasoning.append(base_name)

    result = {"multimodal": multimodal, "reasoning": reasoning}
    cache.set(cache_key, result, settings.OLLAMA_MODELS_CACHE_SECONDS)
    return result


def get_multimodal_models():
    return _get_model_capability_lists()["multimodal"]


def get_models_with_reasoning():
    return _get_model_capability_lists()["reasoning"]


def build_ollama_messages(queryset, max_messages=None):
    max_messages = max_messages or settings.CHAT_MAX_CONTEXT_MESSAGES
    history = list(
        queryset.order_by("-timestamp")[:max_messages].only(
            "sender", "message", "image", "timestamp"
        )
    )
    history.reverse()

    messages = []
    for msg in history:
        if msg.sender == ChatMessage.Sender.SYSTEM:
            continue
        role = (
            "assistant"
            if msg.sender == ChatMessage.Sender.ASSISTANT
            else msg.sender
        )
        entry = {"role": role, "content": msg.message}
        if msg.image:
            entry["images"] = [image_field_to_base64(msg.image)]
        messages.append(entry)
    return messages


def get_api_kwargs(branch):
    return {
        "num_ctx": branch.num_ctx,
        "temperature": branch.temperature,
        "system_prompt": PROMPT_PREFIX + (branch.prompt or ""),
        "think": branch.think,
        "timeout": 300,
    }


def iter_ollama_response(branch, ollama_messages):
    client = get_ollama_client()
    api_kwargs = get_api_kwargs(branch)
    if branch.request_type == ChatBranch.RequestType.CHAT:
        data = {
            "model": branch.selected_model,
            "messages": client.prepare_messages(
                ollama_messages, api_kwargs.get("system_prompt")
            ),
            "think": api_kwargs.get("think", False),
            "stream": True,
            "options": client.build_options(api_kwargs),
        }
        response = client.open_stream("chat", data, timeout=api_kwargs.get("timeout", 300))
        iterator = client.iter_chat_stream
    else:
        data = {
            "model": branch.selected_model,
            "prompt": client.messages_to_prompt(
                ollama_messages, api_kwargs.get("system_prompt")
            ),
            "think": api_kwargs.get("think", False),
            "stream": True,
            "options": client.build_options(api_kwargs),
        }
        response = client.open_stream(
            "generate", data, timeout=api_kwargs.get("timeout", 300)
        )
        iterator = client.iter_generate_stream
    try:
        yield from iterator(response)
    finally:
        response.close()


def collect_ollama_response(branch, ollama_messages):
    client = get_ollama_client()
    api_kwargs = get_api_kwargs(branch)
    if branch.request_type == ChatBranch.RequestType.CHAT:
        result = client.chat(
            branch.selected_model,
            ollama_messages,
            stream=False,
            **api_kwargs,
        )
    else:
        result = client.generate_response(
            branch.selected_model,
            ollama_messages,
            stream=False,
            **api_kwargs,
        )
    message = result.get("message", {})
    return message.get("content", ""), message.get("thinking", "")

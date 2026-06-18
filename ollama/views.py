import logging
import time
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import close_old_connections
from django.db.models import Count
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from prometheus_client import Counter, Histogram
from django_ratelimit.decorators import ratelimit
from requests.exceptions import ConnectionError, RequestException

from .image_processor import (
    delete_branch_chat_images,
    delete_chat_message_images,
    get_validated_image_bytes,
)
from .models import ChatBranch, ChatMessage
from .services import (
    build_ollama_messages,
    collect_ollama_response,
    get_available_models,
    get_models_with_reasoning,
    get_multimodal_models,
    iter_ollama_response,
)
from .sse import format_sse

logger = logging.getLogger(__name__)

CHAT_REQUESTS = Counter(
    "chat_requests_total",
    "Total chat requests",
    ["request_type", "model"],
)
MESSAGE_TYPES = Counter(
    "chat_message_types_total",
    "Count of different message types",
    ["sender", "has_image"],
)
REQUEST_DURATION = Histogram(
    "chat_request_duration_seconds",
    "Duration of chat processing",
    ["request_type", "model"],
)
ERROR_COUNTER = Counter(
    "chat_errors_total",
    "Total errors in chat processing",
    ["error_type"],
)

SYSTEM_ERROR_MESSAGE = "Oops... something went wrong... try again"
STOPPED_SUFFIX = "\n\n*[generation stopped]*"
RATE_LIMIT_MESSAGE = "Too many requests. Please wait a moment and try again."


def _checkbox_enabled(post, name):
    return post.get(name) == "True"


def _apply_branch_from_post(branch, post):
    name = post.get("name", "").strip()
    if not name:
        raise ValueError("Chat name cannot be empty")
    branch.name = name
    branch.description = post.get("description") or None
    branch.prompt = post.get("prompt", "")
    branch.request_type = post.get("request_type", ChatBranch.RequestType.CHAT)
    branch.response_type = post.get(
        "response_type", ChatBranch.ResponseType.STREAM
    )
    branch.selected_model = post.get("model", branch.selected_model)
    branch.temperature = float(post.get("temperature", branch.temperature))
    branch.multimodal = _checkbox_enabled(post, "multimodal")
    branch.think = _checkbox_enabled(post, "think")
    branch.reasoning = _checkbox_enabled(post, "reasoning")
    branch.num_ctx = int(post.get("num_ctx", branch.num_ctx))


def _user_message_payload(message):
    image_url = message.image.url if message.image else None
    return {
        "id": message.id,
        "content": message.message,
        "timestamp": message.timestamp.isoformat(),
        "image_url": image_url,
    }


def _sse_error(message):
    response = StreamingHttpResponse(
        iter([format_sse("error", {"message": message})]),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def _truncate_messages_after(branch, message):
    to_remove = branch.messages.filter(id__gt=message.id)
    removed = list(to_remove.values_list("id", flat=True))
    delete_chat_message_images(to_remove)
    to_remove.delete()
    return removed


def _prepare_regeneration(branch, message_id):
    target = get_object_or_404(ChatMessage, id=message_id, chat_branch=branch)

    if target.sender == ChatMessage.Sender.SYSTEM:
        return None, [], "Cannot regenerate from system messages"

    if target.sender == ChatMessage.Sender.ASSISTANT:
        user_message = (
            branch.messages.filter(sender=ChatMessage.Sender.USER, id__lt=target.id)
            .order_by("-id")
            .first()
        )
        if not user_message:
            return None, [], "No user message found for regeneration"
        to_remove = branch.messages.filter(id__gte=target.id)
        removed_ids = list(to_remove.values_list("id", flat=True))
        delete_chat_message_images(to_remove)
        to_remove.delete()
    else:
        user_message = target
        removed_ids = _truncate_messages_after(branch, target)

    return user_message, removed_ids, None


def _prepare_edit_and_regenerate(branch, message_id, new_content):
    target = get_object_or_404(
        ChatMessage,
        id=message_id,
        chat_branch=branch,
        sender=ChatMessage.Sender.USER,
    )
    new_content = new_content.strip()
    if not new_content:
        return None, [], "Message cannot be empty"

    target.message = new_content
    target.save(update_fields=["message"])
    removed_ids = _truncate_messages_after(branch, target)
    return target, removed_ids, None


def _parse_message_submission(request, branch):
    message_text = request.POST.get("message", "").strip()
    img_file = request.FILES.get("image")
    has_image = img_file is not None
    image_bytes = None

    if img_file:
        try:
            image_bytes = get_validated_image_bytes(img_file)
        except ValueError as exc:
            ERROR_COUNTER.labels(error_type="image_processing").inc()
            return None, str(exc)

    if not message_text and not has_image:
        return None, "Message cannot be empty"

    user_message = ChatMessage.objects.create(
        chat_branch=branch,
        sender=ChatMessage.Sender.USER,
        message=message_text,
    )

    if image_bytes is not None:
        ext = Path(img_file.name).suffix.lower() or ".png"
        user_message.image.save(
            f"{user_message.id}{ext}",
            ContentFile(image_bytes),
            save=True,
        )

    MESSAGE_TYPES.labels(sender="user", has_image=str(has_image)).inc()
    return user_message, None


def _resolve_stream_request(request, branch):
    edit_id = request.POST.get("edit_message_id")
    regenerate_id = request.POST.get("regenerate_message_id")

    if edit_id and regenerate_id:
        return None, [], None, "Invalid request: choose edit or regenerate, not both"

    if edit_id:
        user_message, removed_ids, error = _prepare_edit_and_regenerate(
            branch, edit_id, request.POST.get("message", "")
        )
        if error:
            return None, [], None, error
        return user_message, removed_ids, "message_updated", None

    if regenerate_id:
        user_message, removed_ids, error = _prepare_regeneration(branch, regenerate_id)
        if error:
            return None, removed_ids, None, error
        return user_message, removed_ids, None, None

    user_message, error = _parse_message_submission(request, branch)
    if error:
        return None, [], None, error
    return user_message, [], "user_message", None


def _yield_lead_events(user_message, removed_ids, lead_event):
    if removed_ids:
        yield format_sse("truncated", {"removed_ids": removed_ids})
    if lead_event == "user_message":
        yield format_sse("user_message", _user_message_payload(user_message))
    elif lead_event == "message_updated":
        yield format_sse("message_updated", _user_message_payload(user_message))


def _save_assistant_reply(branch, full_content, full_thinking):
    assistant = ChatMessage.objects.create(
        chat_branch=branch,
        sender=ChatMessage.Sender.ASSISTANT,
        message=full_content,
        think=full_thinking,
    )
    MESSAGE_TYPES.labels(sender="assistant", has_image="False").inc()
    return assistant


def _record_request_metrics(branch, start_time):
    REQUEST_DURATION.labels(
        request_type=branch.request_type,
        model=branch.selected_model,
    ).observe(time.time() - start_time)
    CHAT_REQUESTS.labels(
        request_type="message",
        model=branch.selected_model,
    ).inc()


def _streaming_assistant_reply(branch, user_message, removed_ids=None, lead_event=None):
    close_old_connections()
    start_time = time.time()
    content_parts = []
    thinking_parts = []

    yield from _yield_lead_events(user_message, removed_ids, lead_event)
    ollama_messages = build_ollama_messages(branch.messages)

    try:
        for chunk in iter_ollama_response(branch, ollama_messages):
            if chunk["type"] == "content":
                content_parts.append(chunk["text"])
            elif chunk["type"] == "thinking":
                thinking_parts.append(chunk["text"])
            yield format_sse("chunk", chunk)

        full_content = "".join(content_parts)
        full_thinking = "".join(thinking_parts)

        if full_content:
            assistant = _save_assistant_reply(branch, full_content, full_thinking)
            yield format_sse(
                "done",
                {
                    "message_id": assistant.id,
                    "content": full_content,
                    "thinking": full_thinking,
                    "timestamp": assistant.timestamp.isoformat(),
                },
            )
        else:
            ERROR_COUNTER.labels(error_type="empty_response").inc()
            system_msg = ChatMessage.objects.create(
                chat_branch=branch,
                sender=ChatMessage.Sender.SYSTEM,
                message=SYSTEM_ERROR_MESSAGE,
            )
            yield format_sse(
                "error",
                {"message": SYSTEM_ERROR_MESSAGE, "message_id": system_msg.id},
            )
    except GeneratorExit:
        full_content = "".join(content_parts)
        full_thinking = "".join(thinking_parts)
        if full_content:
            ChatMessage.objects.create(
                chat_branch=branch,
                sender=ChatMessage.Sender.ASSISTANT,
                message=full_content + STOPPED_SUFFIX,
                think=full_thinking,
            )
        raise
    except (ConnectionError, RequestException) as exc:
        ERROR_COUNTER.labels(error_type="connection").inc()
        logger.error("Ollama connection error: %s", exc)
        system_msg = ChatMessage.objects.create(
            chat_branch=branch,
            sender=ChatMessage.Sender.SYSTEM,
            message=SYSTEM_ERROR_MESSAGE,
        )
        yield format_sse(
            "error",
            {"message": SYSTEM_ERROR_MESSAGE, "message_id": system_msg.id},
        )
    except Exception as exc:
        ERROR_COUNTER.labels(error_type="general").inc()
        logger.exception("Stream processing error: %s", exc)
        system_msg = ChatMessage.objects.create(
            chat_branch=branch,
            sender=ChatMessage.Sender.SYSTEM,
            message=SYSTEM_ERROR_MESSAGE,
        )
        yield format_sse(
            "error",
            {"message": SYSTEM_ERROR_MESSAGE, "message_id": system_msg.id},
        )
    finally:
        _record_request_metrics(branch, start_time)
        close_old_connections()


def _onetime_assistant_reply(branch, user_message, removed_ids=None, lead_event=None):
    close_old_connections()
    start_time = time.time()

    yield from _yield_lead_events(user_message, removed_ids, lead_event)
    yield format_sse("generating", {})
    ollama_messages = build_ollama_messages(branch.messages)

    try:
        full_content, full_thinking = collect_ollama_response(branch, ollama_messages)

        if full_content:
            assistant = _save_assistant_reply(branch, full_content, full_thinking)
            yield format_sse(
                "done",
                {
                    "message_id": assistant.id,
                    "content": full_content,
                    "thinking": full_thinking,
                    "timestamp": assistant.timestamp.isoformat(),
                },
            )
        else:
            ERROR_COUNTER.labels(error_type="empty_response").inc()
            system_msg = ChatMessage.objects.create(
                chat_branch=branch,
                sender=ChatMessage.Sender.SYSTEM,
                message=SYSTEM_ERROR_MESSAGE,
            )
            yield format_sse(
                "error",
                {"message": SYSTEM_ERROR_MESSAGE, "message_id": system_msg.id},
            )
    except (ConnectionError, RequestException) as exc:
        ERROR_COUNTER.labels(error_type="connection").inc()
        logger.error("Ollama connection error: %s", exc)
        system_msg = ChatMessage.objects.create(
            chat_branch=branch,
            sender=ChatMessage.Sender.SYSTEM,
            message=SYSTEM_ERROR_MESSAGE,
        )
        yield format_sse(
            "error",
            {"message": SYSTEM_ERROR_MESSAGE, "message_id": system_msg.id},
        )
    except Exception as exc:
        ERROR_COUNTER.labels(error_type="general").inc()
        logger.exception("One-time processing error: %s", exc)
        system_msg = ChatMessage.objects.create(
            chat_branch=branch,
            sender=ChatMessage.Sender.SYSTEM,
            message=SYSTEM_ERROR_MESSAGE,
        )
        yield format_sse(
            "error",
            {"message": SYSTEM_ERROR_MESSAGE, "message_id": system_msg.id},
        )
    finally:
        _record_request_metrics(branch, start_time)
        close_old_connections()


def _stream_assistant_reply(branch, user_message, removed_ids=None, lead_event=None):
    if branch.response_type == ChatBranch.ResponseType.ONETIME:
        yield from _onetime_assistant_reply(
            branch, user_message, removed_ids=removed_ids, lead_event=lead_event
        )
    else:
        yield from _streaming_assistant_reply(
            branch, user_message, removed_ids=removed_ids, lead_event=lead_event
        )


@login_required
def create_chat(request):
    if request.method != "POST":
        return redirect("chat_home")

    try:
        new_branch = ChatBranch(user=request.user)
        _apply_branch_from_post(new_branch, request.POST)
        new_branch.save()
        CHAT_REQUESTS.labels(request_type="create", model=new_branch.selected_model).inc()
        messages.success(request, "Chat successfully created!")
        return redirect("chat_detail", branch_id=new_branch.id)
    except (TypeError, ValueError) as exc:
        ERROR_COUNTER.labels(error_type="create_chat").inc()
        messages.error(request, f"Error: {exc}")
        return redirect("chat_home")


@login_required
def chat_view(request, branch_id=None):
    user = request.user
    today = timezone.now().date()
    available_models = get_available_models()
    branches = ChatBranch.objects.filter(user=user).annotate(
        message_count=Count("messages")
    )
    selected_branch = None
    chat_messages = []

    if branch_id:
        selected_branch = get_object_or_404(ChatBranch, id=branch_id, user=user)
        chat_messages = selected_branch.messages.all()

    return render(
        request,
        "chat/chat.html",
        {
            "branches": branches,
            "selected_branch": selected_branch,
            "messages": chat_messages,
            "today": today,
            "models": available_models,
            "multimodal": get_multimodal_models(),
            "reasoning": get_models_with_reasoning(),
        },
    )


@require_POST
@login_required
@ratelimit(key="user", rate=settings.CHAT_STREAM_RATE, method="POST", block=False)
def stream_message(request, branch_id):
    if getattr(request, "limited", False):
        return _sse_error(RATE_LIMIT_MESSAGE)

    branch = get_object_or_404(ChatBranch, id=branch_id, user=request.user)
    user_message, removed_ids, lead_event, error = _resolve_stream_request(
        request, branch
    )
    if error:
        return _sse_error(error)

    response = StreamingHttpResponse(
        _stream_assistant_reply(
            branch,
            user_message,
            removed_ids=removed_ids,
            lead_event=lead_event,
        ),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@require_POST
@login_required
def edit_chat(request, branch_id):
    branch = get_object_or_404(ChatBranch, id=branch_id, user=request.user)
    try:
        _apply_branch_from_post(branch, request.POST)
        branch.save()
        CHAT_REQUESTS.labels(request_type="edit", model=branch.selected_model).inc()
        messages.success(request, "Chat updated successfully")
    except (TypeError, ValueError) as exc:
        ERROR_COUNTER.labels(error_type="edit_chat").inc()
        messages.error(request, f"Error: {exc}")
    return redirect("chat_detail", branch_id=branch.id)


@require_POST
@login_required
def delete_chat(request, branch_id):
    branch = get_object_or_404(ChatBranch, id=branch_id, user=request.user)
    model_name = branch.selected_model
    saved_branch_id = branch.id
    branch.delete()
    delete_branch_chat_images(saved_branch_id)
    CHAT_REQUESTS.labels(request_type="delete", model=model_name).inc()
    return redirect("chat_home")


@require_POST
@login_required
def delete_all_messages(request, branch_id):
    branch = get_object_or_404(ChatBranch, id=branch_id, user=request.user)
    CHAT_REQUESTS.labels(
        request_type="clear_messages",
        model=branch.selected_model,
    ).inc()
    delete_branch_chat_images(branch.id)
    branch.messages.all().delete()
    return redirect("chat_detail", branch_id=branch.id)

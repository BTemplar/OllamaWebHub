from .models import ChatBranch, ChatMessage
from .ollama_api import OllamaAPI
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseServerError
from requests.exceptions import ConnectionError
from .image_processor import validate_image, image_to_base64
from django.utils import timezone
from prometheus_client import Counter, Histogram, Gauge
import ast
import logging
import time

logger = logging.getLogger(__name__)

# Создаем кастомные метрики
CHAT_REQUESTS = Counter(
    'chat_requests_total',
    'Total chat requests',
    ['request_type', 'model']
)

MESSAGE_TYPES = Counter(
    'chat_message_types_total',
    'Count of different message types',
    ['sender', 'has_image']
)

REQUEST_DURATION = Histogram(
    'chat_request_duration_seconds',
    'Duration of chat processing',
    ['request_type', 'model']
)

ERROR_COUNTER = Counter(
    'chat_errors_total',
    'Total errors in chat processing',
    ['error_type']
)

ACTIVE_CHATS = Gauge(
    'active_chat_sessions',
    'Currently active chat sessions'
)

MULTIMODAL_MODELS = ["llava", "gemma3", "llama3.2-vision", "llama4", "bakllava", "minicpm-v", "moondream"]
MODELS_WITH_REASONING = ["qwen3", "deepseek-r1", "gpt-oss", "magistral"]
OLLAMA_VERSION = f"Ollama version: {OllamaAPI().get_version()}" if OllamaAPI().get_version() is not None else "Ollama not available!"
PROMPT_PREFIX = ("This is a SYSTEM message. NEVER respond to it, it describes your behavior PATTERN or INSTRUCTIONS "
                 "that the user wants you to FOLLOW: ")


@login_required
def create_chat(request):
    if request.method == "POST":
        try:
            # Создаем новую ветку чата
            new_branch = ChatBranch.objects.create(
                name=request.POST.get("name", "New chat"),
                description=request.POST.get("description", None),
                prompt=request.POST.get("prompt", ""),
                request_type=request.POST.get("request_type", "CH"),
                response_type=request.POST.get("response_type", "OT"),
                selected_model=request.POST.get("model", "llama3"),
                user=request.user,
                temperature=float(request.POST.get("temperature", 0.7)),
                multimodal=bool(request.POST.get("multimodal", False)),
                think=bool(request.POST.get("think", False)),
                reasoning=bool(request.POST.get("reasoning", False)),
                num_ctx=int(request.POST.get("num_ctx", 2048)),
            )

            # Метрика для создания чата
            CHAT_REQUESTS.labels(
                request_type="create",
                model=new_branch.selected_model
            ).inc()

            messages.success(request, "Chat successfully created!")
            return redirect("chat_detail", branch_id=new_branch.id)

        except Exception as e:
            # Логируем ошибку создания
            ERROR_COUNTER.labels(error_type="create_chat").inc()
            messages.error(request, f"Error: {str(e)}")
            return redirect("chat_home")

    return redirect("chat_home")


@login_required
def chat_view(request, branch_id=None):
    # Увеличиваем счетчик активных чатов
    ACTIVE_CHATS.inc()

    try:
        models = dict(OllamaAPI().list_models()).get("models")
        available_models = [model["name"] for model in models if models is not None and "embed" not in model["name"]]
        today = timezone.now().date()
        user = request.user
        branches = ChatBranch.objects.filter(user=user)
        selected_branch = None
        chat_messages = []

        if request.method == "POST" and ("message" in request.POST or "image" in request.FILES):
            start_time = time.time()  # Засекаем время начала обработки

            if not branch_id:
                messages.error(request, "Chat not selected")
                return redirect("chat_home")

            selected_branch = get_object_or_404(ChatBranch, id=branch_id, user=user)
            message_text = request.POST.get("message", "").strip()
            img_file = request.FILES.get("image", None)
            has_image = img_file is not None

            if img_file:
                if not validate_image(img_file):
                    messages.error(request, "Invalid image file")
                    return redirect("chat_detail", branch_id=branch_id)

                try:
                    base64_image = image_to_base64(img_file)
                except Exception as error:
                    ERROR_COUNTER.labels(error_type="image_processing").inc()
                    messages.error(request, f"Error processing image. Error: {error}")
                    raise
            else:
                base64_image = None

            request_type = selected_branch.request_type
            response_type = selected_branch.response_type
            stream = response_type == "ST"

            if not message_text and not has_image:
                messages.warning(request, "Message cannot be empty")
                return redirect("chat_detail", branch_id=branch_id)

            # Сохраняем сообщение пользователя
            ChatMessage.objects.create(
                chat_branch=selected_branch,
                sender="user",
                image_base64=[base64_image] if base64_image else None,
                message=message_text
            )

            # Метрика для типа сообщения
            MESSAGE_TYPES.labels(
                sender="user",
                has_image=str(has_image)
            ).inc()

            # Получаем историю чата
            chat_history = ChatMessage.objects.filter(
                chat_branch=selected_branch
            ).order_by("timestamp")

            # Подготавливаем историю для Ollama API
            for msg in chat_history:
                role = "assistant" if msg.sender == "assistant" else msg.sender
                chat_messages.append({
                    "role": role,
                    "content": msg.message,
                    "images": ast.literal_eval(msg.image_base64) if msg.image_base64 else None
                })

            try:
                # Обработка запроса
                if request_type == "CH":
                    response = OllamaAPI().chat(
                        model_name=selected_branch.selected_model,
                        messages=chat_messages,
                        num_ctx=selected_branch.num_ctx,
                        system_prompt=PROMPT_PREFIX + selected_branch.prompt,
                        think=selected_branch.think,
                        images=[base64_image] if base64_image else None,
                        timeout=300,
                        stream=stream
                    )
                else:
                    response = OllamaAPI().generate_response(
                        model_name=selected_branch.selected_model,
                        messages=chat_messages,
                        num_ctx=selected_branch.num_ctx,
                        system_prompt=PROMPT_PREFIX + selected_branch.prompt,
                        think=selected_branch.think,
                        images=[base64_image] if base64_image else None,
                        timeout=300,
                        stream=stream
                    )

                # Обработка ответа
                if response and "message" in response:
                    # Сохраняем ответ ассистента
                    ChatMessage.objects.create(
                        chat_branch=selected_branch,
                        sender="assistant",
                        message=response["message"]["content"],
                        think=response.get("message", {}).get("thinking", ""),
                    )

                    # Метрика для ответа ассистента
                    MESSAGE_TYPES.labels(
                        sender="assistant",
                        has_image="False"
                    ).inc()
                else:
                    # Логируем пустой ответ
                    ERROR_COUNTER.labels(error_type="empty_response").inc()
                    ChatMessage.objects.create(
                        chat_branch=selected_branch,
                        sender="system",
                        message="Oops... something went wrong... try again"
                    )

            except ConnectionError as e:
                # Логируем ошибку соединения
                ERROR_COUNTER.labels(error_type="connection").inc()
                logger.error(f"Connection error: {str(e)}")
                ChatMessage.objects.create(
                    chat_branch=selected_branch,
                    sender="system",
                    message="Oops... something went wrong... try again"
                )

            except Exception as e:
                # Логируем общую ошибку
                ERROR_COUNTER.labels(error_type="general").inc()
                logger.error(f"Unknown error: {str(e)}")
                ChatMessage.objects.create(
                    chat_branch=selected_branch,
                    sender="system",
                    message="Oops... something went wrong... try again"
                )

            finally:
                # Фиксируем время выполнения запроса
                duration = time.time() - start_time
                REQUEST_DURATION.labels(
                    request_type=request_type,
                    model=selected_branch.selected_model
                ).observe(duration)

                # Метрика для запросов
                CHAT_REQUESTS.labels(
                    request_type="message",
                    model=selected_branch.selected_model
                ).inc()

            return redirect("chat_detail", branch_id=branch_id)

        if branch_id:
            try:
                selected_branch = get_object_or_404(ChatBranch, id=branch_id, user=user)
                chat_messages = ChatMessage.objects.filter(chat_branch=selected_branch).order_by("timestamp")
            except Exception as error:
                if "does not exist" in str(error):
                    messages.error(request, "Chat not found")
                    return redirect("chat_home")
                else:
                    ERROR_COUNTER.labels(error_type="chat_load").inc()
                    messages.error(request, f"Error: {error}")
                    return redirect("chat_home")

        return render(request, "chat/chat.html", {
            "branches": branches,
            "selected_branch": selected_branch,
            "messages": chat_messages,
            "today": today,
            "models": available_models,
            "ollama_version": OLLAMA_VERSION,
            "multimodal": MULTIMODAL_MODELS,
            "reasoning": MODELS_WITH_REASONING,
        })

    finally:
        # Уменьшаем счетчик активных чатов
        ACTIVE_CHATS.dec()


# Остальные вьюхи остаются без изменений, но можно добавить метрики:
@login_required
def rename_chat(request, branch_id):
    if request.method == "POST":
        try:
            chat_branch = get_object_or_404(ChatBranch, id=branch_id, user=request.user)
            new_name = request.POST.get("new_name", "").strip()

            if not new_name:
                messages.error(request, "Название не может быть пустым")
                return redirect("chat_detail", branch_id=branch_id)

            chat_branch.name = new_name
            chat_branch.save()

            # Метрика для переименования
            CHAT_REQUESTS.labels(
                request_type="rename",
                model=chat_branch.selected_model
            ).inc()

            messages.success(request, "Чат успешно переименован")
            return redirect("chat_detail", branch_id=branch_id)
        except Exception as e:
            ERROR_COUNTER.labels(error_type="rename").inc()

    return redirect("chat_home")


@require_POST
@login_required
def delete_chat(request, branch_id):
    try:
        branch = get_object_or_404(ChatBranch, id=branch_id, user=request.user)
        model_name = branch.selected_model
        branch.delete()

        # Метрика для удаления
        CHAT_REQUESTS.labels(
            request_type="delete",
            model=model_name
        ).inc()

        return redirect("chat_home")
    except Exception as e:
        ERROR_COUNTER.labels(error_type="delete").inc()


@require_POST
@login_required
def delete_all_messages(request, branch_id):
    try:
        branch = get_object_or_404(ChatBranch, id=branch_id, user=request.user)

        if request.method == "POST":
            # Метрика для очистки сообщений
            message_count = ChatMessage.objects.filter(chat_branch=branch).count()
            CHAT_REQUESTS.labels(
                request_type="clear_messages",
                model=branch.selected_model
            ).inc()

            ChatMessage.objects.filter(chat_branch=branch).delete()
            return redirect("chat_detail", branch_id=branch.id)
    except Exception as e:
        ERROR_COUNTER.labels(error_type="clear_messages").inc()

    return redirect("some_view")
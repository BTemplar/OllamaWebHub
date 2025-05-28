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
import ast
import logging

logger = logging.getLogger(__name__)

models = dict(OllamaAPI().list_models()).get('models')
MULTIMODAL_MODELS = ['llava', 'gemma3', 'llama3.2-vision', 'llama4', 'bakllava', 'minicpm-v', 'moondream']
AVAILABLE_MODELS = [model['name'] for model in models] if models is not None else []
OLLAMA_VERSION = f"Ollama version: {OllamaAPI().get_version()}" if OllamaAPI().get_version() is not None else "Ollama not available!"

@login_required
def create_chat(request):
    if request.method == 'POST':
        try:
            print(request.POST.get('multimodal'))
            # Create a new chat branch
            new_branch = ChatBranch.objects.create(
                name=request.POST.get('name', 'New chat'),
                description=request.POST.get('description', None),
                selected_model=request.POST.get('model', 'llama3'),
                user=request.user,
                temperature=float(request.POST.get('temperature', 0.7)),
                multimodal=bool(request.POST.get('multimodal', False)),
            )

            messages.success(request, 'Chat successfully created!')
            return redirect('chat_detail', branch_id=new_branch.id)

        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('chat_home')

    return redirect('chat_home')


@login_required
def chat_view(request, branch_id=None):
    today = timezone.now().date()
    user = request.user
    branches = ChatBranch.objects.filter(user=user)
    selected_branch = None
    chat_messages = []
    try:
        if request.method == 'POST' and ('message' or 'image') in request.POST:
            if not branch_id:
                messages.error(request, "Chat not selected")
                return redirect('chat_home')

            selected_branch = get_object_or_404(ChatBranch, id=branch_id, user=user)
            message_text = request.POST.get('message', '').strip()
            img_file = request.FILES.get('image', False)

            if img_file:
                img_file = request.FILES.get('image', False)

                if not validate_image(img_file):
                    messages.error(request, "Invalid image file")
                    return redirect('chat_detail', branch_id=branch_id)

                try:
                    base64_image = image_to_base64(img_file)
                except Exception as e:
                    messages.error(request, "Error processing image")
                    raise

            if not message_text:
                messages.warning(request, "Message cannot be empty")
                return redirect('chat_detail', branch_id=branch_id)

            # Save user's message
            ChatMessage.objects.create(
                chat_branch=selected_branch,
                sender='user',
                image_base64=[base64_image] if img_file else None,
                message=message_text
            )

            # Get the entire message history of the thread
            chat_history = ChatMessage.objects.filter(
                chat_branch=selected_branch
            ).order_by('timestamp')

            # Transform ChatMessage objects to a list of dictionaries for Ollama API
            for msg in chat_history:
                role = "assistant" if msg.sender == "assistant" else msg.sender
                chat_messages.append({
                    "role": role,
                    "content": msg.message,
                    "images": ast.literal_eval(msg.image_base64) if msg.image_base64 else None
                })

            try:
                # Use chat_response method instead generate_response
                if not validate_image(img_file):
                    response = OllamaAPI().chat_response(
                        model_name=selected_branch.selected_model,
                        messages=chat_messages,
                        timeout=300,
                        stream=False  # if True, also get stream of tokens
                    )
                else:
                    response = OllamaAPI().chat_multimodal_response(
                        model_name=selected_branch.selected_model,
                        messages=chat_messages,
                        images=[base64_image],
                        timeout=300,
                        stream=False  # if True, also get stream of tokens
                    )

                # Processing the response
                if response and 'message' in response:
                    ChatMessage.objects.create(
                        chat_branch=selected_branch,
                        sender='assistant',
                        message=response['message']['content']
                    )
                else:
                    # Create error message in chat
                    ChatMessage.objects.create(
                        chat_branch=selected_branch,
                        sender='system',
                        message='Oops... something went wrong... try again'
                    )

            except ConnectionError as e:
                logger.error(f"Connection error: {str(e)}")
                # Create system message in chat
                ChatMessage.objects.create(
                    chat_branch=selected_branch,
                    sender='system',
                    message='Oops... something went wrong... try again'
                )

            except Exception as e:
                logger.error(f"Unknown error: {str(e)}")
                ChatMessage.objects.create(
                    chat_branch=selected_branch,
                    sender='system',
                    message='Oops... something went wrong... try again'
                )

            return redirect('chat_detail', branch_id=branch_id)

        if branch_id:
            selected_branch = get_object_or_404(ChatBranch, id=branch_id, user=user)
            chat_messages = ChatMessage.objects.filter(chat_branch=selected_branch).order_by('timestamp')

        return render(request, 'chat/chat.html', {
            'branches': branches,
            'selected_branch': selected_branch,
            'messages': chat_messages,
            'today': today,
            'models': AVAILABLE_MODELS,
            'ollama_version': OLLAMA_VERSION,
            'multimodal': MULTIMODAL_MODELS,
        })

    except Exception as e:
        logger.exception(f"Critical error in chat_view: {e}")
        return HttpResponseServerError("Internal Server Error")


@login_required
def rename_chat(request, branch_id):
    if request.method == 'POST':
        chat_branch = get_object_or_404(ChatBranch, id=branch_id, user=request.user)
        new_name = request.POST.get('new_name', '').strip()

        if not new_name:
            messages.error(request, "Название не может быть пустым")
            return redirect('chat_detail', branch_id=branch_id)

        chat_branch.name = new_name
        chat_branch.save()
        messages.success(request, "Чат успешно переименован")
        return redirect('chat_detail', branch_id=branch_id)

    return redirect('chat_home')

@require_POST
@login_required
def delete_chat(request, branch_id):
    branch = get_object_or_404(ChatBranch, id=branch_id, user=request.user)
    branch.delete()
    return redirect('chat_home')

@require_POST
@login_required
def delete_all_messages(request, branch_id):
    branch = get_object_or_404(ChatBranch, id=branch_id, user=request.user)

    if request.method == 'POST':
        ChatMessage.objects.filter(chat_branch=branch).delete()

        return redirect('chat_detail', branch_id=branch.id)

    return redirect('some_view')
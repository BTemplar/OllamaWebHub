from .models import ChatBranch, ChatMessage
from .ollama_api import OllamaAPI
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseServerError
from requests.exceptions import ConnectionError
import logging

logger = logging.getLogger(__name__)

@login_required
def create_chat(request):
    if request.method == 'POST':
        try:
            # Создаем чат
            new_branch = ChatBranch.objects.create(
                name=request.POST.get('name', 'New chat'),
                user=request.user
            )
            messages.success(request, 'Chat successfully created!')
            return redirect('chat_detail', branch_id=new_branch.id)

        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('chat_home')

    return redirect('chat_home')


@login_required
def chat_view(request, branch_id=None):
    user = request.user
    branches = ChatBranch.objects.filter(user=user)
    selected_branch = None
    chat_messages = []

    try:
        if request.method == 'POST' and 'message' in request.POST:
            if not branch_id:
                messages.error(request, "Chat not selected")
                return redirect('chat_home')

            selected_branch = get_object_or_404(ChatBranch, id=branch_id, user=user)
            message_text = request.POST.get('message', '').strip()

            if not message_text:
                messages.warning(request, "Message cannot be empty")
                return redirect('chat_detail', branch_id=branch_id)

            # Сохраняем сообщение пользователя
            ChatMessage.objects.create(
                chat_branch=selected_branch,
                sender='user',
                message=message_text
            )

            try:
                # Попытка получить ответ от Ollama
                ollama = OllamaAPI()
                response = ollama.generate_response(
                    model_name='llama2',
                    prompt=message_text
                )

                if response and 'response' in response:
                    ChatMessage.objects.create(
                        chat_branch=selected_branch,
                        sender='ollama',
                        message=response['response']
                    )
                else:
                    # Создаем сообщение об ошибке в чате
                    ChatMessage.objects.create(
                        chat_branch=selected_branch,
                        sender='system',
                        message='Oops... something went wrong... try again'
                    )

            except ConnectionError as e:
                logger.error(f"Connection error: {str(e)}")
                # Создаем системное сообщение в чате
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
        })

    except Exception as e:
        logger.exception(f"Critical error in chat_view: {e}")
        return HttpResponseServerError("Internal Server Error")


@require_POST
@login_required
def delete_chat(request, branch_id):
    branch = get_object_or_404(ChatBranch, id=branch_id, user=request.user)
    branch.delete()
    return redirect('chat_home')
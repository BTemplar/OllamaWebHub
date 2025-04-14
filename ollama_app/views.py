from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from .models import ChatBranch, ChatMessage
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.forms import ModelForm, ChoiceField, NumberInput

def chat_branch_list(request):
    branches = ChatBranch.objects.filter(user=request.user)
    return render(request, 'ollama_app/chat_branch_list.html', {'branches': branches})

@login_required
def chat_branch_create(request):
    if request.method == 'POST':
        # Получаем данные из формы
        name = request.POST['name']
        description = request.POST.get('description', '') # Опциональное описание

        # Создаем ветку чата
        branch = ChatBranch.objects.create(name=name, user=request.user, description=description)
        return redirect('chat_branch_list')
    else:
        return render(request, 'ollama_app/chat_branch_create.html')

@login_required
def chat_branch_delete(request, pk):
    branch = get_object_or_404(ChatBranch, pk=pk, user=request.user)
    branch.delete()
    return redirect('chat_branch_list')

@login_required
def chat_view(request, pk):
    branch = get_object_or_404(ChatBranch, pk=pk, user=request.user)
    messages = ChatMessage.objects.filter(chat_branch=branch).order_by('timestamp')
    return render(request, 'ollama_app/chat_view.html', {'branch': branch, 'messages': messages})

def send_message(request, pk):
    # Получаем сообщение от пользователя
    user_message = request.POST['message']

    # Получаем ветку чата
    branch = get_object_or_404(ChatBranch, pk=pk, user=request.user)

    # Создаем сообщение пользователя
    ChatMessage.objects.create(chat_branch=branch, sender='user', message=user_message)

    # Отправляем сообщение в Ollama API (здесь нужна интеграция)
    # ollama_response = send_to_ollama(user_message, branch)

    # Создаем ответ от Ollama
    # ChatMessage.objects.create(chat_branch=branch, sender='ollama', message=ollama_response)

    return redirect('chat_view', pk=pk)

class TemperatureChoiceField(ChoiceField):
    def __init__(self, choices=None):
        super().__init__(choices=[
            (0.1, '0.1'),
            (0.3, '0.3'),
            (0.5, '0.5'),
            (0.7, '0.7'),
            (1.0, '1.0'),
        ])

class ModelChoiceField(ChoiceField):
    def __init__(self, choices=None):
        super().__init__(choices=[
            ('llama2', 'Llama 2'),
            ('mistral', 'Mistral'),
            # Добавь другие модели, доступные в Ollama
        ])


class ChatViewForm(ModelForm):
    temperature = TemperatureChoiceField()
    model = ModelChoiceField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['temperature'].initial = '0.7' # Значение по умолчанию
        self.fields['model'].initial = 'llama2'  # Значение по умолчанию

@login_required
def chat_view(request, pk):
    branch = get_object_or_404(ChatBranch, pk=pk, user=request.user)
    messages = ChatMessage.objects.filter(chat_branch=branch).order_by('timestamp')

    if request.method == 'POST':
        form = ChatViewForm(request.POST)
        if form.is_valid():
            user_message = form.data['user_message']
            temperature = form.data['temperature']
            model = form.data['model']

            # Отправляем сообщение в Ollama API с учетом температуры и модели
            ollama_response = send_to_ollama(user_message, branch, temperature, model)

            # Создаем ответ от Ollama
            ChatMessage.objects.create(chat_branch=branch, sender='olllama', message=ollama_response)

            return redirect('chat_view', pk=pk)
    else:
        form = ChatViewForm()

    return render(request, 'ollemma_app/chat_view.html', {'branch': branch, 'messages': messages, 'form': form})
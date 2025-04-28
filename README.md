# Django Chat Application with Ollama Integration

A web-based chat application built with Django, integrated with the Ollama API for AI-powered responses. Users can create chat threads, interact with different AI models, and manage their chat history.

## Features

- **User Authentication**: Secure login system for personalized chat experiences.
- **Chat Management**:
  - Create new chat threads with custom names and descriptions.
  - Rename or delete existing chats.
  - View chat history with timestamps.
- **AI Integration**:
  - Select from available Ollama models (e.g., `llama3`).
  - Real-time interaction with AI-generated responses.
  - Error handling for API connectivity issues.
- **Message History**: Persistent storage of all user and AI messages.
- **Ollama Status**: Display available models and Ollama server version.

## Technologies

- **Backend**: Django 4.x
- **AI API**: [Ollama](https://ollama.ai/)
- **Database**: SQLite (default; can be configured for PostgreSQL/MySQL)
- **Frontend**: Django Templates
- **Dependencies**:
  - `requests` for API communication
  - `python-dotenv` for environment variables (recommended)

## Installation

### Prerequisites
- Python 3.9+
- Ollama server running locally (see [Ollama Setup](#ollama-setup))
- Django 4.x

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/django-ollama-chat.git
   cd django-ollama-chat
   
2. Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    venv\Scripts\activate     # Windows
   
3. Install dependencies:
    ```bash
    pip install django requests python-dotenv
   
4. Configure environment variables (create .env file):
    ```ini
   OLLAMA_API_HOST=http://localhost:11434
   SECRET_KEY=your-django-secret-key
   
5. Apply migrations:
   ```bash
   python manage.py migrate
   
6. Run the development server:
   ```bash
   python manage.py runserver
   
## Ollama Setup

1. Install and run [Ollama](ollama.com)
2. Pull desired models (e.g.):
   ```bash
   ollama pull llama3
   
## Usage
1. **Access the app**: Visit http://localhost:8000 in your browser.
2. **Authenticate**: Log in or register a new account.
3. **Create a Chat**:
    * Click "New Chat"
    * Select an AI model (e.g., llama3)
    * Add optional name/description
4. **Chat Interface**:
    * Type messages in the input field
    * View AI responses in real-time
    * Use sidebar to switch between chats
5. **Manage Chats**:
    * Rename chats via the chat header
    * Delete chats using the trash icon
## Project Structure
```
.
├── account/               # Authentication app
│   ├── views.py           # Authentication logic
│   ├── forms.py           # Authentication forms
│   ├── urls.py            # Authentication app url tracing
├── ollama_app/            # Main app
│   ├── models.py          # ChatBranch, ChatMessage models
│   ├── views.py           # Core logic (provided)
│   ├── ollama_api.py      # Ollama API wrapper
│   ├── urls.py            # Main app url tracing
├── templates/             # HTML templates
├── OllamaWebHub/          # Django project config
└── .env                   # Environment variables
# Ollama WebHub

Django chat application integrated with the [Ollama](https://ollama.com/) API. Users can create chat threads, pick AI models, send text and images, and manage chat history.

## Features

- User authentication (login / register)
- Create, edit, and delete chat threads (model, prompt, temperature, stream vs one-time response, etc.)
- Ollama integration: model list, chat and generate modes, streaming (aggregated server-side)
- Multimodal chats for vision models
- Reasoning / thinking display for supported models
- Markdown rendering with syntax highlighting
- Real-time SSE streaming of assistant responses in the chat UI
- Stop generation mid-stream
- Edit user messages with automatic regeneration
- Regenerate assistant or user messages
- Prometheus metrics at `/metrics`

## Stack

- Django 5.2
- SQLite (default)
- Ollama API
- Bootstrap 5

## Prerequisites

- Python 3.12+
- Ollama server running locally or remotely

## Installation

```bash
git clone https://github.com/BTemplar/OllamaWebHub.git
cd OllamaWebHub

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

pip install -r requirements.txt
cp .env.example .env            # then edit values
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://localhost:8000

## Configuration

Copy `.env.example` to `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | dev placeholder |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `OLLAMA_API_URL` | Ollama API base URL | `http://localhost:11434/api` |
| `CHAT_MAX_CONTEXT_MESSAGES` | Messages sent to Ollama | `50` |
| `CHAT_MAX_IMAGE_SIZE_BYTES` | Max upload size for chat images | `10485760` (10 MB) |
| `CHAT_STREAM_RATE` | Rate limit for stream endpoint (per user) | `30/m` |
| `OLLAMA_MODELS_CACHE_SECONDS` | Model list cache TTL | `60` |
| `METRICS_ALLOWED_IPS` | IPs allowed to scrape metrics in production | `127.0.0.1` |

## Ollama setup

```bash
ollama pull llama3
ollama serve
```

## Project structure

```
.
├── accounts/          # Authentication
├── core/              # Django project settings
├── ollama/            # Chat app, Ollama client, services
├── templates/         # HTML templates
├── static/            # Static assets
├── .env.example       # Environment template
└── manage.py
```

## License

MIT — see [LICENSE.txt](LICENSE.txt).

Author: Oleg Rud · GitHub: [@BTemplar](https://github.com/BTemplar)

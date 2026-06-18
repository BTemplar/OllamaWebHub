# Ollama WebHub

Django chat application integrated with the [Ollama](https://ollama.com/) API. Users can create chat threads, pick AI models, send text and images, and manage chat history.

## Features

### Authentication & access
- User login and logout
- Optional public registration (`REGISTRATION_ENABLED`)
- Per-user chat isolation

### Chat management
- Create, edit, and delete chat threads
- System prompt, temperature, context window (`num_ctx`), and model selection per thread
- Request mode: multi-turn **Chat** or single **Response**
- Response delivery: **Stream** (token-by-token) or **One-time** (full reply)
- Clear all messages in a thread without deleting the thread itself

### Ollama integration
- Model list from the Ollama server (cached, embedding models excluded)
- Ollama connection status shown in the UI
- Automatic model capability detection (vision / multimodal, reasoning)
- Chat and generate API modes
- Configurable context limit (`CHAT_MAX_CONTEXT_MESSAGES`)

### Multimodal & reasoning
- Image uploads for vision-capable models (validated with Pillow, size-limited)
- Images stored on disk under `media/chat_images/` and sent to Ollama as base64
- Automatic cleanup of image files when messages or threads are deleted
- Optional thinking / reasoning for supported models
- Collapsible reasoning blocks in the chat UI

### Chat UI
- Real-time SSE streaming of assistant responses
- Stop generation mid-stream
- Edit user messages with automatic regeneration
- Regenerate assistant or user messages
- Markdown rendering with syntax highlighting (Pygments)
- Copy and download buttons for code blocks
- Expandable fullscreen chat layout

### Operations
- Prometheus metrics at `/metrics` (IP-restricted when `DEBUG=False`)
- Rate limiting on the stream endpoint (`CHAT_STREAM_RATE`)
- Production-oriented security headers when `DEBUG=False`

## Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.2 |
| Database | SQLite (default) |
| LLM API | Ollama REST API |
| Images | Pillow |
| Markdown | Markdown + Pygments |
| UI | Bootstrap 5, vanilla JavaScript |
| Metrics | django-prometheus |
| Rate limiting | django-ratelimit |

## Prerequisites

- Python 3.12+
- Ollama server running locally or on a remote host

## Installation

```bash
git clone https://github.com/BTemplar/OllamaWebHub.git
cd OllamaWebHub

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

pip install -r requirements.txt
copy .env.example .env        # Windows: copy | Linux/macOS: cp
# Edit .env with your values

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://localhost:8000

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | dev placeholder |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `REGISTRATION_ENABLED` | Allow public user sign-up | `True` |
| `OLLAMA_API_URL` | Ollama API base URL | `http://localhost:11434/api` |
| `CHAT_MAX_CONTEXT_MESSAGES` | Max messages sent to Ollama per request | `50` |
| `CHAT_MAX_IMAGE_SIZE_BYTES` | Max upload size for chat images | `10485760` (10 MB) |
| `CHAT_STREAM_RATE` | Rate limit for the stream endpoint (per user) | `30/m` |
| `OLLAMA_MODELS_CACHE_SECONDS` | TTL for cached model list and Ollama status | `60` |
| `METRICS_ALLOWED_IPS` | IPs allowed to scrape `/metrics` when `DEBUG=False` | `127.0.0.1` |

When `DEBUG=False`, set a strong `SECRET_KEY`, configure `ALLOWED_HOSTS`, and restrict `METRICS_ALLOWED_IPS` to your Prometheus scraper. With an empty `METRICS_ALLOWED_IPS` list, metrics remain open only while `DEBUG=True`.

## Ollama setup

```bash
ollama pull llama3
ollama serve
```

For vision models, pull a multimodal model (for example `llava`) and enable **Multimodal** when creating or editing a chat. For reasoning models, enable **Reasoning enabled** and optionally **Show reasoning in UI**.

## Running tests

```bash
python manage.py test ollama
```

## Project structure

```
.
├── accounts/              # Login, registration, auth context
├── core/                  # Django settings, URLs, metrics view
├── ollama/                # Chat app
│   ├── image_processor.py # Image validation, storage paths, cleanup
│   ├── ollama_api.py      # Ollama HTTP client
│   ├── services.py        # Model cache, message building, streaming
│   ├── sse.py             # Server-Sent Events helpers
│   ├── signals.py         # Image file cleanup on message delete
│   ├── views.py           # Chat UI and stream endpoint
│   └── tests.py           # Image processor unit tests
├── templates/             # HTML templates (chat, accounts)
├── static/                # CSS and JavaScript (chat UI, modals, uploads)
├── media/                 # Uploaded chat images (created at runtime)
├── .env.example           # Environment template
└── manage.py
```

## License

MIT — see [LICENSE.txt](LICENSE.txt).

Author: Oleg Rud · GitHub: [@BTemplar](https://github.com/BTemplar)

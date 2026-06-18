import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_client = None


def get_ollama_client():
    global _client
    if _client is None:
        _client = OllamaAPI(api_url=settings.OLLAMA_API_URL)
    return _client


class OllamaAPI:
    def __init__(self, api_url=None):
        self.api_url = api_url or settings.OLLAMA_API_URL

    def get_version(self):
        try:
            response = requests.get(f"{self.api_url}/version", timeout=10)
            response.raise_for_status()
            return response.json()["version"]
        except requests.exceptions.RequestException as exc:
            logger.warning("Failed to get Ollama version: %s", exc)
            return None

    def list_models(self):
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            logger.warning("Failed to list Ollama models: %s", exc)
            return None

    def pull_model(self, model_name, insecure=False, stream=False):
        params = {"name": model_name, "insecure": insecure, "stream": stream}
        try:
            response = requests.post(
                f"{self.api_url}/pull", params=params, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to pull model %s: %s", model_name, exc)
            return None

    def delete_model(self, model_name):
        try:
            response = requests.delete(
                f"{self.api_url}/delete",
                json={"name": model_name},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to delete model %s: %s", model_name, exc)
            return None

    def build_options(self, kwargs):
        return {
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 1.0),
            "top_k": kwargs.get("top_k", 50),
            "repeat_penalty": kwargs.get("repeat_penalty", 1.0),
            "num_ctx": kwargs.get("num_ctx", 2048),
        }

    def prepare_messages(self, messages, system_prompt=None):
        prepared = []
        for message in messages:
            entry = {"role": message["role"], "content": message.get("content", "")}
            if message.get("images"):
                entry["images"] = message["images"]
            prepared.append(entry)
        if system_prompt:
            prepared.insert(0, {"role": "system", "content": system_prompt})
        return prepared

    def messages_to_prompt(self, messages, system_prompt=None):
        parts = []
        if system_prompt:
            parts.append(f"system: {system_prompt}")
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            parts.append(f"{role}: {content}")
        parts.append("assistant:")
        return "\n".join(parts)

    def _consume_chat_stream(self, response):
        content_parts = []
        thinking_parts = []
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Invalid JSON in stream chunk: %s", exc)
                continue
            message = chunk.get("message", {})
            if message.get("content"):
                content_parts.append(message["content"])
            if message.get("thinking"):
                thinking_parts.append(message["thinking"])
        return {
            "message": {
                "content": "".join(content_parts),
                "thinking": "".join(thinking_parts),
            }
        }

    def _consume_generate_stream(self, response):
        content_parts = []
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Invalid JSON in stream chunk: %s", exc)
                continue
            if chunk.get("response"):
                content_parts.append(chunk["response"])
        return {"message": {"content": "".join(content_parts), "thinking": ""}}

    def iter_chat_stream(self, response):
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Invalid JSON in stream chunk: %s", exc)
                continue
            message = chunk.get("message", {})
            if message.get("content"):
                yield {"type": "content", "text": message["content"]}
            if message.get("thinking"):
                yield {"type": "thinking", "text": message["thinking"]}

    def iter_generate_stream(self, response):
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Invalid JSON in stream chunk: %s", exc)
                continue
            if chunk.get("response"):
                yield {"type": "content", "text": chunk["response"]}

    def open_stream(self, endpoint, data, timeout=300):
        response = requests.post(
            f"{self.api_url}/{endpoint}",
            json=data,
            stream=True,
            timeout=timeout,
        )
        response.raise_for_status()
        return response

    def stream_chat(self, model_name, messages, **kwargs):
        data = {
            "model": model_name,
            "messages": self.prepare_messages(
                messages, kwargs.get("system_prompt")
            ),
            "think": kwargs.get("think", False),
            "stream": True,
            "options": self.build_options(kwargs),
        }
        response = self.open_stream("chat", data, timeout=kwargs.get("timeout", 300))
        yield from self.iter_chat_stream(response)

    def stream_generate(self, model_name, messages, **kwargs):
        data = {
            "model": model_name,
            "prompt": self.messages_to_prompt(
                messages, kwargs.get("system_prompt")
            ),
            "think": kwargs.get("think", False),
            "stream": True,
            "options": self.build_options(kwargs),
        }
        response = self.open_stream("generate", data, timeout=kwargs.get("timeout", 300))
        yield from self.iter_generate_stream(response)

    def _post(self, endpoint, data, timeout=300):
        stream = data.get("stream", False)
        try:
            response = requests.post(
                f"{self.api_url}/{endpoint}",
                json=data,
                stream=stream,
                timeout=timeout,
            )
            response.raise_for_status()
            if not stream:
                payload = response.json()
                if endpoint == "generate" and "message" not in payload:
                    return {
                        "message": {
                            "content": payload.get("response", ""),
                            "thinking": "",
                        }
                    }
                return payload
            if endpoint == "generate":
                return self._consume_generate_stream(response)
            return self._consume_chat_stream(response)
        except requests.exceptions.RequestException as exc:
            logger.error("Ollama %s request failed: %s", endpoint, exc)
            raise

    def chat(self, model_name, messages, **kwargs):
        data = {
            "model": model_name,
            "messages": self.prepare_messages(
                messages, kwargs.get("system_prompt")
            ),
            "think": kwargs.get("think", False),
            "stream": kwargs.get("stream", False),
            "options": self.build_options(kwargs),
        }
        return self._post("chat", data, timeout=kwargs.get("timeout", 300))

    def generate_response(self, model_name, messages, **kwargs):
        data = {
            "model": model_name,
            "prompt": self.messages_to_prompt(
                messages, kwargs.get("system_prompt")
            ),
            "think": kwargs.get("think", False),
            "stream": kwargs.get("stream", False),
            "options": self.build_options(kwargs),
        }
        return self._post("generate", data, timeout=kwargs.get("timeout", 300))

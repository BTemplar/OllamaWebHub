import json
import logging
from typing import Any, Iterator, Optional

import requests
from django.conf import settings
from requests import Response
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

_client: Optional["OllamaAPI"] = None


def get_ollama_client() -> "OllamaAPI":
    """
    Return a process-wide singleton Ollama API client.

    Returns:
        OllamaAPI: Shared client instance configured from Django settings.
    """
    global _client
    if _client is None:
        _client = OllamaAPI(api_url=settings.OLLAMA_API_URL)
    return _client


class OllamaAPI:
    """HTTP client for the Ollama REST API."""

    def __init__(self, api_url: Optional[str] = None) -> None:
        """
        Initialize the API client.

        Args:
            api_url (Optional[str]): Base API URL; defaults to Django settings.
        """
        self.api_url = api_url or settings.OLLAMA_API_URL

    def get_version(self) -> Optional[str]:
        """
        Fetch the Ollama server version string.

        Returns:
            Optional[str]: Version string, or None when the request fails.
        """
        try:
            response = requests.get(f"{self.api_url}/version", timeout=10)
            response.raise_for_status()
            return response.json()["version"]
        except RequestException as exc:
            logger.warning("Failed to get Ollama version: %s", exc)
            return None

    def list_models(self) -> Optional[dict[str, Any]]:
        """
        List models available on the Ollama server.

        Returns:
            Optional[dict[str, Any]]: Parsed JSON payload, or None on failure.
        """
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=10)
            response.raise_for_status()
            return response.json()
        except RequestException as exc:
            logger.warning("Failed to list Ollama models: %s", exc)
            return None

    def show_model(self, model_name: str) -> Optional[dict[str, Any]]:
        """
        Fetch metadata and capabilities for a single model.

        Args:
            model_name (str): Full Ollama model name.

        Returns:
            Optional[dict[str, Any]]: Parsed JSON payload, or None on failure.
        """
        try:
            response = requests.post(
                f"{self.api_url}/show",
                json={"model": model_name},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except RequestException as exc:
            logger.warning("Failed to show model %s: %s", model_name, exc)
            return None

    def pull_model(
        self, model_name: str, insecure: bool = False, stream: bool = False
    ) -> Optional[dict[str, Any]]:
        """
        Pull a model from the Ollama registry.

        Args:
            model_name (str): Model name to pull.
            insecure (bool): Allow insecure connections when pulling.
            stream (bool): Whether to stream pull progress from the API.

        Returns:
            Optional[dict[str, Any]]: Parsed JSON payload, or None on failure.
        """
        params = {"name": model_name, "insecure": insecure, "stream": stream}
        try:
            response = requests.post(
                f"{self.api_url}/pull", params=params, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except RequestException as exc:
            logger.error("Failed to pull model %s: %s", model_name, exc)
            return None

    def delete_model(self, model_name: str) -> Optional[dict[str, Any]]:
        """
        Delete a model from the local Ollama instance.

        Args:
            model_name (str): Model name to delete.

        Returns:
            Optional[dict[str, Any]]: Parsed JSON payload, or None on failure.
        """
        try:
            response = requests.delete(
                f"{self.api_url}/delete",
                json={"name": model_name},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except RequestException as exc:
            logger.error("Failed to delete model %s: %s", model_name, exc)
            return None

    def build_options(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        Map high-level generation kwargs to Ollama option fields.

        Args:
            kwargs (dict[str, Any]): Generation settings such as temperature.

        Returns:
            dict[str, Any]: Options object accepted by the Ollama API.
        """
        return {
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 1.0),
            "top_k": kwargs.get("top_k", 50),
            "repeat_penalty": kwargs.get("repeat_penalty", 1.0),
            "num_ctx": kwargs.get("num_ctx", 2048),
        }

    def prepare_messages(
        self,
        messages: list[dict[str, Any]],
        system_prompt: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Normalize chat messages and optionally prepend a system prompt.

        Args:
            messages (list[dict[str, Any]]): Conversation messages.
            system_prompt (Optional[str]): Optional system instruction text.

        Returns:
            list[dict[str, Any]]: Messages ready for the Ollama chat endpoint.
        """
        prepared = []
        for message in messages:
            entry = {"role": message["role"], "content": message.get("content", "")}
            if message.get("images"):
                entry["images"] = message["images"]
            prepared.append(entry)
        if system_prompt:
            prepared.insert(0, {"role": "system", "content": system_prompt})
        return prepared

    def messages_to_prompt(
        self,
        messages: list[dict[str, Any]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Convert chat messages into a single prompt for the generate endpoint.

        Args:
            messages (list[dict[str, Any]]): Conversation messages.
            system_prompt (Optional[str]): Optional system instruction text.

        Returns:
            str: Flattened prompt ending with an assistant prefix.
        """
        parts = []
        if system_prompt:
            parts.append(f"system: {system_prompt}")
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            parts.append(f"{role}: {content}")
        parts.append("assistant:")
        return "\n".join(parts)

    def _consume_chat_stream(self, response: Response) -> dict[str, Any]:
        """
        Aggregate a streaming chat response into a single payload.

        Args:
            response (Response): Open streaming HTTP response.

        Returns:
            dict[str, Any]: Combined message content and thinking text.
        """
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

    def _consume_generate_stream(self, response: Response) -> dict[str, Any]:
        """
        Aggregate a streaming generate response into a single payload.

        Args:
            response (Response): Open streaming HTTP response.

        Returns:
            dict[str, Any]: Combined assistant message content.
        """
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

    def iter_chat_stream(self, response: Response) -> Iterator[dict[str, str]]:
        """
        Yield normalized chunks from a streaming chat response.

        Args:
            response (Response): Open streaming HTTP response.

        Yields:
            dict[str, str]: Chunk dictionaries with ``type`` and ``text`` keys.
        """
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

    def iter_generate_stream(self, response: Response) -> Iterator[dict[str, str]]:
        """
        Yield normalized chunks from a streaming generate response.

        Args:
            response (Response): Open streaming HTTP response.

        Yields:
            dict[str, str]: Chunk dictionaries with ``type`` and ``text`` keys.
        """
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

    def open_stream(
        self, endpoint: str, data: dict[str, Any], timeout: int = 300
    ) -> Response:
        """
        Open a streaming POST request to an Ollama endpoint.

        Args:
            endpoint (str): API path segment, e.g. ``chat`` or ``generate``.
            data (dict[str, Any]): JSON request body.
            timeout (int): Request timeout in seconds.

        Returns:
            Response: Open streaming HTTP response.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
        """
        response = requests.post(
            f"{self.api_url}/{endpoint}",
            json=data,
            stream=True,
            timeout=timeout,
        )
        response.raise_for_status()
        return response

    def stream_chat(
        self, model_name: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> Iterator[dict[str, str]]:
        """
        Stream chat completion chunks for the given model and messages.

        Args:
            model_name (str): Ollama model name.
            messages (list[dict[str, Any]]): Conversation messages.
            **kwargs (Any): Additional generation options.

        Yields:
            dict[str, str]: Normalized content and thinking chunks.
        """
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

    def stream_generate(
        self, model_name: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> Iterator[dict[str, str]]:
        """
        Stream generate-completion chunks for the given model and messages.

        Args:
            model_name (str): Ollama model name.
            messages (list[dict[str, Any]]): Conversation messages.
            **kwargs (Any): Additional generation options.

        Yields:
            dict[str, str]: Normalized content chunks.
        """
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

    def _post(
        self, endpoint: str, data: dict[str, Any], timeout: int = 300
    ) -> dict[str, Any]:
        """
        Send a POST request to an Ollama endpoint.

        Args:
            endpoint (str): API path segment, e.g. ``chat`` or ``generate``.
            data (dict[str, Any]): JSON request body.
            timeout (int): Request timeout in seconds.

        Returns:
            dict[str, Any]: Parsed JSON payload or aggregated stream result.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
        """
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
        except RequestException as exc:
            logger.error("Ollama %s request failed: %s", endpoint, exc)
            raise

    def chat(
        self, model_name: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """
        Run a chat completion request against Ollama.

        Args:
            model_name (str): Ollama model name.
            messages (list[dict[str, Any]]): Conversation messages.
            **kwargs (Any): Additional generation options.

        Returns:
            dict[str, Any]: Parsed API response or aggregated stream result.
        """
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

    def generate_response(
        self, model_name: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """
        Run a generate completion request against Ollama.

        Args:
            model_name (str): Ollama model name.
            messages (list[dict[str, Any]]): Conversation messages.
            **kwargs (Any): Additional generation options.

        Returns:
            dict[str, Any]: Parsed API response or aggregated stream result.
        """
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

import requests
import json


class OllamaAPI:
    def __init__(self, api_url="http://localhost:11434/api"):
        """Initialize the Ollama API client with the specified base URL."""
        self.api_url = api_url

    def get_version(self):
        """
        Send a GET request to retrieve the Ollama version.

        Returns:
            str: The version of Ollama if successful, None otherwise.
        """
        try:
            response = requests.get(
                f"{self.api_url}/version",
                timeout=30
            )
            response.raise_for_status()
            return response.json()["version"]
        except requests.exceptions.RequestException as e:
            print(f"Error getting version: {e}")
            return None

    def pull_model(self, model_name, insecure=False, stream=False):
        """
        Download a model from the Ollama API.

        Args:
            model_name (str): The name of the model to download.
            insecure (bool, optional): Allow insecure connections. Defaults to False.
            stream (bool, optional): Stream the download. Defaults to False.

        Returns:
            dict: JSON response if successful, None otherwise.
        """
        params = {
            "name": model_name,
            "insecure": insecure,
            "stream": stream
        }

        try:
            response = requests.post(
                f"{self.api_url}/pull",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error downloading model: {e}")
            return None

    def push_model(self, model_name, insecure=False, stream=False):
        """
        Push a model to the Ollama API.

        Args:
            model_name (str): The name of the model to push.
            insecure (bool, optional): Allow insecure connections. Defaults to False.
            stream (bool, optional): Stream the upload. Defaults to False.

        Returns:
            dict: JSON response if successful, None otherwise.
        """
        params = {
            "model": model_name,
            "insecure": insecure,
            "stream": stream
        }

        try:
            response = requests.post(
                f"{self.api_url}/push",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error loading model: {e}")
            return None

    def create_model_from_safetensors(self, model_name, files):
        """
        Create a model using safetensors files.

        Args:
            model_name (str): The name of the model.
            files (list): List of safetensors files.

        Returns:
            dict: JSON response if successful, None otherwise.
        """
        data = {
            "model": model_name,
            "files": files
        }

        try:
            response = requests.post(
                f"{self.api_url}/create",
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating model: {e}")
            return None

    def delete_model(self, model_name):
        """
        Delete a specified model.

        Args:
            model_name (str): The name of the model to delete.

        Returns:
            dict: JSON response if successful, None otherwise.
        """
        try:
            response = requests.delete(
                f"{self.api_url}/models/{model_name}",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error deleting model: {e}")
            return None

    def list_models(self):
        """
        Retrieve a list of available models.

        Returns:
            list: List of models if successful, None otherwise.
        """
        try:
            response = requests.get(
                f"{self.api_url}/tags",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error listing models: {e}")
            return None

    def _generate_response(self, endpoint, data):
        """
        Common method for generating responses.

        Args:
            endpoint (str): The API endpoint.
            data (dict): The request data.

        Returns:
            Union[dict, Generator]: JSON response or generator if streaming.
        """
        try:
            response = requests.post(
                f"{self.api_url}/{endpoint}",
                json=data,
                stream=True
            )
            response.raise_for_status()

            if not data.get("stream", False):
                return response.json()

            def stream_generator():
                for line in response.iter_lines():
                    if line:
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError as e:
                            print(f"Error decoding JSON: {e}")
                return

            return stream_generator()

        except requests.exceptions.RequestException as e:
            print(f"Error generating response: {e}")
            return None

    def generate_response(self, model_name, messages, **kwargs):
        """
        Generate a response using the specified model and messages.

        Args:
            model_name (str): The name of the model.
            messages (list): List of message dictionaries.
            **kwargs: Additional parameters like temperature, top_p, etc.

        Returns:
            Union[dict, Generator]: JSON response or generator if streaming.
        """
        options = {
            "temperature": kwargs.get("temperature", 1.0),
            "top_p": kwargs.get("top_p", 1.0),
            "top_k": kwargs.get("top_k", 50),
            "repeat_penalty": kwargs.get("repeat_penalty", 1.0),
            "num_ctx": kwargs.get("num_ctx", 2048)
        }

        data = {
            "model": model_name,
            "messages": messages,
            "think": kwargs.get("think", True),
            "stream": kwargs.get("stream", False),
            **options
        }

        if kwargs.get("system_prompt"):
            system_message = {
                "role": "system",
                "content": kwargs["system_prompt"]
            }
            data["messages"].append(system_message)

        return self._generate_response("generate", data)

    def chat(self, model_name, messages, **kwargs):
        """
        Generate a response in chat format.

        Args:
            model_name (str): The name of the model.
            messages (list): List of message dictionaries.
            **kwargs: Additional parameters like temperature, top_p, etc.

        Returns:
            Union[dict, Generator]: JSON response or generator if streaming.
        """
        options = {
            "temperature": kwargs.get("temperature", 1.0),
            "top_p": kwargs.get("top_p", 1.0),
            "top_k": kwargs.get("top_k", 50),
            "repeat_penalty": kwargs.get("repeat_penalty", 1.0),
            "num_ctx": kwargs.get("num_ctx", 2048)
        }

        data = {
            "model": model_name,
            "messages": messages,
            "think": kwargs.get("think", True),
            "stream": kwargs.get("stream", False),
            **options
        }

        if kwargs.get("system_prompt"):
            system_message = {
                "role": "system",
                "content": kwargs["system_prompt"]
            }
            data["messages"].append(system_message)

        return self._generate_response("chat", data)

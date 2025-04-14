import requests
import json

class OllamaAPI:
    def __init__(self, api_url="http://localhost:11434/api"):
        self.api_url = api_url

    def get_version(self):
        """Получает версию Ollama."""
        try:
            response = requests.get(f"{self.api_url}/version", timeout=10)
            response.raise_for_status()
            return response.json()['version']
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении версии: {e}")
            return None

    def pull_model(self, model_name, insecure=False, stream=False):
        """Скачивает модель."""
        params = {'name': model_name}
        if insecure:
            params['insecure'] = True
        if stream:
            params['stream'] = True

        try:
            response = requests.post(f"{self.api_url}/pull", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при скачивании модели: {e}")
            return None

    def push_model(self, model_name, insecure=False, stream=False):
        """Загружает модель."""
        params = {'model': model_name}
        if insecure:
            params['insecure'] = True
        if stream:
            params['stream'] = True
        try:
            response = requests.post(f"{self.api_url}/push", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при загрузке модели: {e}")
            return None

    def create_model_from_safetensors(self, model_name, files):
        """Создает модель из директории с файлами в формате safetensors."""
        data = {'model': model_name, 'files': json.dumps(files)}
        try:
            response = requests.post(f"{self.api_url}/create", data=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при создании модели: {e}")
            return None

    def delete_model(self, model_name):
        """Удаляет модель."""
        try:
            response = requests.delete(f"{self.api_url}/models/{model_name}", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при удалении модели: {e}")
            return None

    def list_models(self):
        """Получает список доступных моделей."""
        try:
            response = requests.get(f"{self.api_url}/models", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении списка моделей: {e}")
            return None

    def generate_response(self, model_name, prompt, temperature=0.7, top_p=0.95, top_k=40, repeat_penalty=1.1, stream=False):
        """Генерирует ответ от модели."""
        data = {
            "model": model_name,
            "prompt": prompt,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repeat_penalty": repeat_penalty,
        }
        if stream:
            data["stream"] = True

        try:
            response = requests.post(f"{self.api_url}/generate", json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при генерации ответа: {e}")
            return None

    def generate_multimodal_response(self, model_name, prompt, images=None, temperature=0.7):
        """
        Генерирует ответ от мультимодальной модели.

        Args:
            model_name (str): Название мультимодальной модели.
            prompt (str): Текстовый запрос.
            images (list, optional): Список base64-encoded изображений. Defaults to None.
            temperature (float, optional): Температура для генерации ответа. Defaults to 0.7.

        Returns:
            dict: Ответ от модели.
        """

        data = {
            "model": model_name,
            "prompt": prompt,
            "temperature": temperature,
        }

        if images:
            data["images"] = images

        try:
            response = requests.post(f"{self.api_url}/generate", json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при генерации ответа: {e}")
            return None
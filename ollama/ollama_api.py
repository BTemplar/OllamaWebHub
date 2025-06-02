import requests
import json

class OllamaAPI:
    def __init__(self, api_url="http://localhost:11434/api"):
        self.api_url = api_url


    def get_version(self):
        """
        Gets the Ollama version.

        This function sends a GET request to the Ollama API to retrieve the version information.
        It returns the version if the request is successful, otherwise it prints an error message and returns None.

        Returns:
            str: The Ollama version if the request is successful, None otherwise.
        """
        try:
            response = requests.get(f"{self.api_url}/version", timeout=30)
            response.raise_for_status()
            return response.json()['version']
        except requests.exceptions.RequestException as e:
            print(f"Error getting version: {e}")
            return None


    def pull_model(self, model_name, insecure=False, stream=False):
        """
        Downloads the model.

        Args:
            model_name (str): The name of the model to download.
            insecure (bool, optional): Whether to allow insecure connections. Defaults to False.
            stream (bool, optional): Whether to stream the download. Defaults to False.

        Returns:
            dict: The JSON response from the API if the request is successful, None otherwise.
        """
        params = {'name': model_name}
        if insecure:
            params['insecure'] = True
        if stream:
            params['stream'] = True

        try:
            response = requests.post(f"{self.api_url}/pull", params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error downloading model: {e}")
            return None


    def push_model(self, model_name, insecure=False, stream=False):
        """
        Pushes the model to the Ollama API.

        Args:
            model_name (str): The name of the model to push.
            insecure (bool, optional): Whether to allow insecure connections. Defaults to False.
            stream (bool, optional): Whether to stream the upload. Defaults to False.

        Returns:
            dict: The JSON response from the API if the request is successful, None otherwise.
        """
        params = {'model': model_name}
        if insecure:
            params['insecure'] = True
        if stream:
            params['stream'] = True

        try:
            response = requests.post(f"{self.api_url}/push", params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error loading model: {e}")
            return None


    def create_model_from_safetensors(self, model_name, files):
        """
        Creates a model from a directory of safetensors files.

        Args:
            model_name (str): The name of the model to create.
            files (list): A list of safetensors files to use for creating the model.

        Returns:
            dict: The JSON response from the API if the request is successful, None otherwise.
        """
        data = {'model': model_name, 'files': json.dumps(files)}
        try:
            response = requests.post(f"{self.api_url}/create", data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating model: {e}")
            return None


    def delete_model(self, model_name):
        """
        Deletes the model.

        Args:
            model_name (str): The name of the model to delete.

        Returns:
            dict: The JSON response from the API if the request is successful, None otherwise.
        """
        try:
            response = requests.delete(f"{self.api_url}/models/{model_name}", timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error deleting model: {e}")
            return None


    def list_models(self):
        """
        Gets a list of available models.

        Returns:
            list: A list of available models if the request is successful, None otherwise.
        """
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting list of models: {e}")
            return None


    def generate_response(self, model_name, messages, images=None, tools=None, format=None, temperature=0.7,
                                 top_p=0.95, top_k=40, num_ctx=2048, think = False, repeat_penalty=1.1, options=None,
                                 stream=False, keep_alive=None, system_prompt=None, timeout=30):
        """
        Generates a chat response using the specified model and parameters.

        Args:
            model_name (str): The name of the model to use for generating the response.
            messages (list): A list of messages to use for generating the response.
            images (list, optional): A list of base64-encoded images. Defaults to None.
            tools (list, optional): A list of tools to use for generating the response. Defaults to None.
            format (str, optional): The format of the response. Defaults to None.
            temperature (float, optional): The temperature to use for generating the response. Defaults to 0.7.
            top_p (float, optional): The top_p to use for generating the response. Defaults to 0.95.
            top_k (int, optional): The top_k to use for generating the response. Defaults to 40.
            num_ctx (int, optional): The maximum number of tokens to use for generating the response. Defaults to 2048.
            think (bool, optional): Whether to generate a response with thinking. Defaults to True.
            repeat_penalty (float, optional): The repeat_penalty to use for generating the response. Defaults to 1.1.
            options (dict, optional): Additional options for generating the response. Defaults to None.
            stream (bool, optional): Whether to stream the response. Defaults to False.
            keep_alive (bool, optional): Controls how long the model will stay loaded into memory following the request (default: 5m). Defaults to None.
            system_prompt (str, optional): The system prompt to use for generating the response. Defaults to None.
            timeout (int, optional): The timeout for the request. Defaults to 30.

        Returns:
            dict: The JSON response from the API if the request is successful, None otherwise.
        """

        options_dict = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repeat_penalty": repeat_penalty,
            "num_ctx": num_ctx,
        }
        if options:
            options_dict.update(options)

        data = {
            "model": model_name,
            "message": messages,
            "think": think,
            "stream": stream,
        }

        if images:
            data["images"] = images

        if tools is not None:
            data["tools"] = tools
        if format is not None:
            data["format"] = format
        if keep_alive is not None:
            data["keep_alive"] = keep_alive
        if options_dict:
            data["options"] = options_dict

        if system_prompt:
            system_message = {"role": "system",
                                   "content": f"{system_prompt}"
                                   }
            data["messages"].append(system_message)

        try:
            response = requests.post(
                f"{self.api_url}/generate",
                json=data,
                timeout=timeout,
                stream=stream
            )
            response.raise_for_status()

            if stream:
                def stream_generator():
                    try:
                        for line in response.iter_lines():
                            if line:
                                try:
                                    yield json.loads(line)
                                except json.JSONDecodeError as e:
                                    print(f"Error decoding JSON: {e}")
                    except requests.exceptions.RequestException as e:
                        print(f"Error streaming: {e}")

                return stream_generator()
            else:
                return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error generating chat response: {e}")
            return None


    def chat_response(self, model_name, messages, images=None, tools=None, format=None, temperature=0.7,
                                 top_p=0.95, top_k=40, num_ctx=2048, think = False, repeat_penalty=1.1, options=None,
                                 stream=False, keep_alive=None, system_prompt=None, timeout=30):
        """
        Generates a chat response using the specified model and parameters.

        Args:
            model_name (str): The name of the model to use for generating the response.
            messages (list): A list of messages to use for generating the response.
            images (list, optional): A list of base64-encoded images. Defaults to None.
            tools (list, optional): A list of tools to use for generating the response. Defaults to None.
            format (str, optional): The format of the response. Defaults to None.
            temperature (float, optional): The temperature to use for generating the response. Defaults to 0.7.
            top_p (float, optional): The top_p to use for generating the response. Defaults to 0.95.
            top_k (int, optional): The top_k to use for generating the response. Defaults to 40.
            num_ctx (int, optional): The maximum number of tokens to use for generating the response. Defaults to 2048.
            think (bool, optional): Whether to generate a response with thinking. Defaults to True.
            repeat_penalty (float, optional): The repeat_penalty to use for generating the response. Defaults to 1.1.
            options (dict, optional): Additional options for generating the response. Defaults to None.
            stream (bool, optional): Whether to stream the response. Defaults to False.
            keep_alive (bool, optional): Controls how long the model will stay loaded into memory following the request (default: 5m). Defaults to None.
            system_prompt (str, optional): The system prompt to use for generating the response. Defaults to None.
            timeout (int, optional): The timeout for the request. Defaults to 30.

        Returns:
            dict: The JSON response from the API if the request is successful, None otherwise.
        """

        options_dict = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repeat_penalty": repeat_penalty,
            "num_ctx": num_ctx,
        }
        if options:
            options_dict.update(options)

        data = {
            "model": model_name,
            "messages": messages,
            "think": think,
            "stream": stream,
        }

        if images:
            data["images"] = images

        if tools is not None:
            data["tools"] = tools
        if format is not None:
            data["format"] = format
        if keep_alive is not None:
            data["keep_alive"] = keep_alive
        if options_dict:
            data["options"] = options_dict

        if system_prompt:
            system_message = {"role": "system",
                                   "content": f"{system_prompt}"
                                   }
            data["messages"].append(system_message)

        try:
            response = requests.post(
                f"{self.api_url}/chat",
                json=data,
                timeout=timeout,
                stream=stream
            )
            response.raise_for_status()

            if stream:
                def stream_generator():
                    try:
                        for line in response.iter_lines():
                            if line:
                                try:
                                    yield json.loads(line)
                                except json.JSONDecodeError as e:
                                    print(f"Error decoding JSON: {e}")
                    except requests.exceptions.RequestException as e:
                        print(f"Error streaming: {e}")

                return stream_generator()
            else:
                return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error generating chat response: {e}")
            return None

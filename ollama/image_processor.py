from PIL import Image
import io
import base64
from typing import Any
from ast import literal_eval


def validate_image(file: Any) -> bool:
    """
    Validate an image file.
    This function validates an image file by attempting to open it with the Pillow library.
    If the file is a valid image, it returns True. If the file is not a valid image, it returns False.

    Args:
        file (Any): The image file to validate.

    Returns:
        bool: True if the file is a valid image, False otherwise.
    """
    try:
        file.seek(0)
        image_data = file.read()
        with Image.open(io.BytesIO(image_data)) as img:
            img.verify()
        return True
    except Exception:
        return False


def image_to_base64(file: Any) -> str:
    """
    Convert an image file to base64.
    This function converts an image file to base64 by reading the file and encoding it using base64.
    Args:
        file (Any): The image file to convert.

    Returns:
        str: The base64 representation of the image file.

    Raises:
        ValueError: If there is an error converting the file to base64.
    """
    try:
        is_image = validate_image(file)
        if not is_image:
            raise ValueError('The image file must be a valid image.')
        else:
            file.seek(0)
            image_data = file.read()
            return base64.b64encode(image_data).decode('utf-8')
    except Exception as error:
        if isinstance(error, ValueError):
            raise error
        raise ValueError("Error converting file to base64") from error

def base64_to_image(base64_str: str) -> Image.Image:
    """
    Converts a base64 string to an image.

    Args:
        base64_str (str): The base64 string to convert.

    Returns:
        Image.Image: The converted image.

    Raises:
        ValueError: If the input data is not a valid base64 string.
    """
    try:
        image_data = base64.b64decode(base64_str)
        img = Image.open(io.BytesIO(image_data))

        mime_type = img.format.lower()

        return f"data:{mime_type};base64,{literal_eval(base64_str)}"
    except Exception as error:
        raise ValueError("Invalid image data") from error

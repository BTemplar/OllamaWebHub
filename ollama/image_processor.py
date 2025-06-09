from PIL import Image
import io
import base64
from typing import Any
from ast import literal_eval


def validate_image(file: Any) -> bool:
    """
    Validate an image file using Pillow (PIL).

    Args:
        file (Any): The image file to validate, expected to be a binary stream.

    Returns:
        bool: True if the file is a valid image, False otherwise.
    """
    try:
        # Read the file content
        file.seek(0)
        image_data = file.read()

        # Use Pillow to attempt opening and verifying the image
        with Image.open(io.BytesIO(image_data)) as img:
            img.verify()  # This raises an exception if the image is invalid

        return True
    except (IOError, ValueError, Image.DecompressionBombError):
        # Catch specific exceptions related to image processing
        return False


def image_to_base64(file: Any) -> str:
    """
    Convert a validated image file stream into a base64 encoded string.

    Args:
        file (Any): The image file stream that has been validated.

    Returns:
        str: The base64 encoded string of the image.

    Raises:
        ValueError: If the file is not a valid image or if conversion fails.
    """
    try:
        # Ensure the file is valid
        if not validate_image(file):
            raise ValueError("The provided file is not a valid image.")

        # Read the file content for encoding
        file.seek(0)
        image_data = file.read()
        base64_str = base64.b64encode(image_data).decode('utf-8')

        return base64_str
    except Exception as e:
        raise ValueError(f"Failed to convert image to base64: {str(e)}") from e


def base64_to_image(base64_str: str) -> Image.Image:
    """
    Convert a base64 encoded string into an Pillow (PIL) Image object.

    Args:
        base64_str (str): The base64 encoded string representing the image.

    Returns:
        Image.Image: A PIL Image object of the decoded image.

    Raises:
        ValueError: If the input is not a valid base64 string or if decoding fails.
    """
    try:
        # Decode the base64 string into bytes
        decoded_image_bytes = base64.b64decode(base64_str)

        # Open the image using Pillow's Image.open with BytesIO
        img = Image.open(io.BytesIO(decoded_image_bytes))
        mime_type = img.format.lower()

        return f"data:{mime_type};base64,{literal_eval(base64_str)}"

    except (base64.binascii.Error, IOError) as error:
        raise ValueError(f"Invalid base64 data or unable to decode image: {str(error)}") from error
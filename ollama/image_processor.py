import base64
import io
import shutil
import uuid
from pathlib import Path
from typing import Any, Optional

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import QuerySet
from django.db.models.fields.files import FieldFile
from PIL import Image


def chat_message_image_path(instance: Any, filename: str) -> str:
    """
    Build a unique upload path for a chat message image.

    Args:
        instance: Chat message model instance (used for branch id).
        filename (str): Original uploaded file name.

    Returns:
        str: Relative media path for storage.
    """
    ext = Path(filename).suffix.lower() or ".png"
    return f"chat_images/branch_{instance.chat_branch_id}/{uuid.uuid4().hex}{ext}"


def branch_chat_images_dir(branch_id: int) -> Path:
    """
    Return the on-disk directory for all images of a chat branch.

    Args:
        branch_id (int): Chat branch primary key.

    Returns:
        Path: Absolute path to the branch image directory.
    """
    return Path(settings.MEDIA_ROOT) / "chat_images" / f"branch_{branch_id}"


def delete_stored_chat_image(image_name: str) -> None:
    """
    Delete a single stored chat image file if a name is provided.

    Args:
        image_name (str): Relative path inside the default storage backend.
    """
    if image_name:
        default_storage.delete(image_name)


def delete_chat_message_images(messages: QuerySet) -> None:
    """
    Delete image files referenced by the given chat messages queryset.

    Args:
        messages (QuerySet): ChatMessage queryset whose images should be removed.
    """
    image_names = messages.exclude(image="").exclude(image__isnull=True).values_list(
        "image", flat=True
    )
    for image_name in image_names:
        delete_stored_chat_image(image_name)


def delete_branch_chat_images(branch_id: int) -> None:
    """
    Remove the entire on-disk image directory for a chat branch.

    Args:
        branch_id (int): Chat branch primary key.
    """
    branch_dir = branch_chat_images_dir(branch_id)
    if branch_dir.is_dir():
        shutil.rmtree(branch_dir)


def _max_image_size() -> int:
    """
    Return the configured maximum allowed image size in bytes.

    Returns:
        int: Maximum image size from Django settings.
    """
    return settings.CHAT_MAX_IMAGE_SIZE_BYTES


def get_validated_image_bytes(
    file: Any, max_size_bytes: Optional[int] = None
) -> bytes:
    """
    Read and validate an uploaded image file.

    Args:
        file: File-like object with optional ``size``, ``seek``, and ``read``.
        max_size_bytes (Optional[int]): Size limit override; defaults to settings.

    Returns:
        bytes: Raw validated image bytes.

    Raises:
        ValueError: If the file exceeds the size limit or is not a valid image.
    """
    max_size_bytes = max_size_bytes or _max_image_size()
    file_size = getattr(file, "size", None)
    if isinstance(file_size, int) and file_size > max_size_bytes:
        raise ValueError(
            f"Image file exceeds maximum allowed size ({max_size_bytes // (1024 * 1024)} MB)."
        )
    file.seek(0)
    data = file.read(max_size_bytes + 1)
    if len(data) > max_size_bytes:
        raise ValueError(
            f"Image file exceeds maximum allowed size ({max_size_bytes // (1024 * 1024)} MB)."
        )
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except (IOError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError("The provided file is not a valid image.") from exc
    return data


def validate_image(file: Any, max_size_bytes: Optional[int] = None) -> bool:
    """
    Check whether an uploaded file is a valid image within the size limit.

    Args:
        file: File-like object to validate.
        max_size_bytes (Optional[int]): Size limit override; defaults to settings.

    Returns:
        bool: True if the file is valid, False otherwise.
    """
    try:
        get_validated_image_bytes(file, max_size_bytes)
        file.seek(0)
        return True
    except ValueError:
        file.seek(0)
        return False


def image_to_base64(file: Any, max_size_bytes: Optional[int] = None) -> str:
    """
    Convert a validated image file to a base64-encoded string.

    Args:
        file: File-like object containing image data.
        max_size_bytes (Optional[int]): Size limit override; defaults to settings.

    Returns:
        str: Base64-encoded image bytes.

    Raises:
        ValueError: If validation fails or the file cannot be read.
    """
    try:
        data = get_validated_image_bytes(file, max_size_bytes)
        return base64.b64encode(data).decode("utf-8")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Error processing image: {exc}") from exc


def image_field_to_base64(image_field: FieldFile) -> str:
    """
    Read a Django ImageField and return its contents as base64 text.

    Args:
        image_field (FieldFile): Stored image field on a model instance.

    Returns:
        str: Base64-encoded image bytes.
    """
    with image_field.open("rb") as handle:
        return base64.b64encode(handle.read()).decode("utf-8")

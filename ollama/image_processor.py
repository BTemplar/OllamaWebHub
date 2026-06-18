import base64
import io
import shutil
import uuid
from pathlib import Path
from typing import Any, Optional

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import QuerySet
from PIL import Image


def chat_message_image_path(instance, filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".png"
    return f"chat_images/branch_{instance.chat_branch_id}/{uuid.uuid4().hex}{ext}"


def branch_chat_images_dir(branch_id: int) -> Path:
    return Path(settings.MEDIA_ROOT) / "chat_images" / f"branch_{branch_id}"


def delete_stored_chat_image(image_name: str) -> None:
    if image_name:
        default_storage.delete(image_name)


def delete_chat_message_images(messages: QuerySet) -> None:
    image_names = messages.exclude(image="").exclude(image__isnull=True).values_list(
        "image", flat=True
    )
    for image_name in image_names:
        delete_stored_chat_image(image_name)


def delete_branch_chat_images(branch_id: int) -> None:
    branch_dir = branch_chat_images_dir(branch_id)
    if branch_dir.is_dir():
        shutil.rmtree(branch_dir)


def _max_image_size() -> int:
    return settings.CHAT_MAX_IMAGE_SIZE_BYTES


def get_validated_image_bytes(file: Any, max_size_bytes: Optional[int] = None) -> bytes:
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
    try:
        get_validated_image_bytes(file, max_size_bytes)
        file.seek(0)
        return True
    except ValueError:
        file.seek(0)
        return False


def image_to_base64(file: Any, max_size_bytes: Optional[int] = None) -> str:
    try:
        data = get_validated_image_bytes(file, max_size_bytes)
        return base64.b64encode(data).decode("utf-8")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Error processing image: {exc}") from exc


def image_field_to_base64(image_field) -> str:
    with image_field.open("rb") as handle:
        return base64.b64encode(handle.read()).decode("utf-8")

import io
import base64
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from ollama.image_processor import get_validated_image_bytes, image_to_base64, validate_image


def create_valid_image_bytes():
    img = Image.new("RGB", (100, 100), color="red")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    return img_byte_arr.getvalue()


class TestValidateImage(unittest.TestCase):
    def test_valid_image(self):
        valid_image = io.BytesIO(create_valid_image_bytes())
        self.assertTrue(validate_image(valid_image))

    def test_invalid_image(self):
        invalid_image = io.BytesIO(b"invalid image data")
        self.assertFalse(validate_image(invalid_image))

    def test_oversized_image_rejected(self):
        oversized = io.BytesIO(create_valid_image_bytes())
        oversized.size = 20 * 1024 * 1024
        self.assertFalse(validate_image(oversized, max_size_bytes=1024))

    def test_file_pointer_reset_after_validation(self):
        content = create_valid_image_bytes()
        file = io.BytesIO(content)
        file.seek(0)
        validate_image(file)
        self.assertEqual(file.tell(), 0)


class TestImageToBase64(unittest.TestCase):
    def test_successful_conversion(self):
        valid_image = io.BytesIO(create_valid_image_bytes())
        base64_str = image_to_base64(valid_image)
        decoded_data = base64.b64decode(base64_str)
        self.assertEqual(decoded_data, create_valid_image_bytes())

    def test_invalid_image_raises_error(self):
        invalid_image = io.BytesIO(b"invalid data")
        with self.assertRaises(ValueError) as context:
            image_to_base64(invalid_image)
        self.assertEqual(
            str(context.exception), "The provided file is not a valid image."
        )

    def test_validate_image_called(self):
        with patch("ollama.image_processor.get_validated_image_bytes") as mock_get:
            mock_get.return_value = b"data"
            file = io.BytesIO(b"data")
            image_to_base64(file)
            mock_get.assert_called_once_with(file, None)

    def test_read_error_wrapped(self):
        with patch(
            "ollama.image_processor.get_validated_image_bytes",
            side_effect=OSError("Read error"),
        ):
            with self.assertRaises(ValueError) as context:
                image_to_base64(io.BytesIO(b"data"))
            self.assertEqual(str(context.exception), "Error processing image: Read error")


class TestGetValidatedImageBytes(unittest.TestCase):
    def test_mock_file_read(self):
        mock_file = MagicMock()
        mock_file.size = 100
        mock_file.read.return_value = create_valid_image_bytes()
        data = get_validated_image_bytes(mock_file)
        self.assertEqual(data, create_valid_image_bytes())


if __name__ == "__main__":
    unittest.main()

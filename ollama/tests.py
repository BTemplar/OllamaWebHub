import unittest
from unittest.mock import patch, MagicMock
import io
import base64
from PIL import Image
from ollama.image_processor import validate_image, image_to_base64

def create_valid_image_bytes():
    """Creates the bytes of a valid PNG image."""
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

class TestValidateImage(unittest.TestCase):
    def test_valid_image(self):
        valid_image = io.BytesIO(create_valid_image_bytes())
        self.assertTrue(validate_image(valid_image))

    def test_invalid_image(self):
        invalid_image = io.BytesIO(b'invalid image data')
        self.assertFalse(validate_image(invalid_image))

    def test_file_pointer_position_after_validation(self):
        content = b'fake image data'
        file = io.BytesIO(content)
        file.seek(5)
        validate_image(file)
        # After validate_image: seek(0) and read(), position at end
        self.assertEqual(file.tell(), len(content))

class TestImageToBase64(unittest.TestCase):
    def test_successful_conversion(self):
        valid_image = io.BytesIO(create_valid_image_bytes())
        base64_str = image_to_base64(valid_image)
        decoded_data = base64.b64decode(base64_str)
        # We check that the decoded data matches the original data.
        self.assertEqual(decoded_data, create_valid_image_bytes())

    def test_invalid_image_raises_error(self):
        invalid_image = io.BytesIO(b'invalid data')
        with self.assertRaises(ValueError) as context:
            image_to_base64(invalid_image)
        self.assertEqual(str(context.exception), 'The image file must be a valid image.')

    def test_validate_image_called(self):
        with patch('ollama.image_processor.validate_image') as mock_validate:
            mock_validate.return_value = True
            file = io.BytesIO(b'data')
            image_to_base64(file)
            mock_validate.assert_called_once_with(file)

    def test_file_seek_and_read_called(self):
        mock_file = MagicMock()
        mock_file.read.return_value = create_valid_image_bytes()
        with patch('ollama.image_processor.validate_image', return_value=True):
            image_to_base64(mock_file)
            mock_file.seek.assert_any_call(0)
            mock_file.read.assert_called_once()

    def test_error_during_read_raises_value_error(self):
        mock_file = MagicMock()
        mock_file.read.side_effect = Exception("Read error")
        with patch('ollama.image_processor.validate_image', return_value=True):
            with self.assertRaises(ValueError) as context:
                image_to_base64(mock_file)
            self.assertEqual(str(context.exception), "Error converting file to base64")

if __name__ == '__main__':
    unittest.main()

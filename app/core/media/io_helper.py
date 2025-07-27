import base64
import os

def from_base64_to_image(base64_string: str) -> bytes:
    """
    Convert a base64 string to an image.
    """
    image_data = base64.b64decode(base64_string)
    return image_data

def from_image_to_base64(image_path: str) -> str:
    """
    Convert an image to a base64 string.
    """
    # Validate the input
    if not image_path or not isinstance(image_path, str):
        raise ValueError("Image path must be a non-empty string")
    
    # Check if file exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Clean the path to remove any potential null bytes
    clean_path = image_path.replace('\x00', '')
    
    with open(clean_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def save_image_to_disk(image_data: bytes, image_path: str) -> None:
    """
    Save an image to disk.
    """
    with open(image_path, "wb") as image_file:
        image_file.write(image_data)

def delete_image_from_disk(image_path: str) -> None:
    """
    Delete an image from disk.
    """
    if os.path.exists(image_path):
        os.remove(image_path)

def load_image_from_disk(image_path: str) -> bytes:
    """
    Load an image from disk.
    """
    # Validate the input
    if not image_path or not isinstance(image_path, str):
        raise ValueError("Image path must be a non-empty string")
    
    # Check if file exists
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Clean the path to remove any potential null bytes
    clean_path = image_path.replace('\x00', '')
    
    with open(clean_path, "rb") as image_file:
        return image_file.read()
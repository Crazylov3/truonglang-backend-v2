import uuid
import hashlib

def generate_transaction_reference(prefix: str = "TRN", length: int = 32):
    """
    Generate a unique transaction reference. have 64 characters
    """
    unique_id = f"{prefix}-{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    return hashlib.sha256(unique_id.encode()).hexdigest()[:length]

import hashlib
import os

def compute_sha256(file_path: str, chunk_size: int = 65536) -> str:
    """
    Computes the SHA-256 hash of a file without modifying or locking it.
    Strict read-only operation.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found for hashing: {file_path}")
        
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
            
    return sha256.hexdigest()

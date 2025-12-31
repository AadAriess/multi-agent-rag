"""
Utilitas umum untuk aplikasi
"""
import os
import uuid
from typing import Optional
from pathlib import Path


def generate_unique_id() -> str:
    """
    Menghasilkan ID unik
    """
    return str(uuid.uuid4())


def save_file(content: bytes, directory: str, filename: Optional[str] = None) -> str:
    """
    Menyimpan file ke sistem
    """
    if filename is None:
        filename = generate_unique_id()
    
    # Membuat direktori jika belum ada
    Path(directory).mkdir(parents=True, exist_ok=True)
    
    file_path = os.path.join(directory, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    
    return file_path


def read_file(file_path: str) -> Optional[bytes]:
    """
    Membaca file dari sistem
    """
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None


def delete_file(file_path: str) -> bool:
    """
    Menghapus file dari sistem
    """
    try:
        os.remove(file_path)
        return True
    except FileNotFoundError:
        return False
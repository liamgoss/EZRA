# Ephemeral File Handling

import io, os, time
from zipfile import ZipFile
from pathlib import Path
from typing import List
from encryption import encrypt_file, decrypt_file



def timestomp(files: List[Path]):
    """
    Given a file path, set its last access and modification times to 0 (epoch time).
    """
    for file in files:
        try:
            os.utime(file, (0, 0))
        except Exception as e:
            print(f"Failed to timestomp {file} with error: {e}")


def pad_file_reasonably(path: Path):
    """
    | .ezra Size | Padding Goal                    |
    |------------|---------------------------------|
    | < 1MB      | Pad to 1MB                      |
    | 1MB-10MB   | Round up to nearest MB          |
    | 10MB+      | Round up to nearest 5MB or 10MB |
    """
    size = path.stat().st_size
    if size < 1 * 1024 * 1024:
        target = 1 * 1024 * 1024
    elif size < 10 * 1024 * 1024:
        target = ((size // (1024 * 1024)) + 1) * 1024 * 1024  # Round up to next MB
    else:
        target = ((size // (5 * 1024 * 1024)) + 1) * 5 * 1024 * 1024  # Round to 5MB
    pad_file_to_exact_size(path, target)

def pad_file_to_exact_size(path: Path, target_bytes: int = 100):
    """
    Pad .ezrm and .ezrd files to consistent size (e.g. 100 Bytes)
    """
    current = path.stat().st_size
    if current < target_bytes:
        with open(path, "ab") as f:
            f.write(b'\x00' * (target_bytes - current))
    


def create_ezra_archive(filepaths: list[Path]) -> bytes:
    """
    Given a list of file paths, create an in-memory ZIP archive containing them.
    Returns the raw bytes of the zip archive.
    """
    zip_buffer = io.BytesIO()
    with ZipFile(zip_buffer, 'w') as zipf:
        for path in filepaths:
            arcname = path.name  # filename remains inside archive, but not leaked in storage
            zipf.write(path, arcname=arcname)
    return zip_buffer.getvalue()


def encrypt_files_to_ezra(filepaths: List[Path]) -> dict:
    """
    Archive and encrypt one or more files into a single encrypted blob.

    Returns dict: {
        "ciphertext": bytes,
        "key": bytes,
        "nonce": bytes
    }
    """
    zip_bytes = create_ezra_archive(filepaths)
    return encrypt_file(zip_bytes)

def decrypt_ezra_to_files(ciphertext: bytes, key: bytes, nonce: bytes, output_dir: Path) -> list[Path]:
    """
    Decrypts an encrypted .ezra archive and extracts its contents to output_dir.
    
    Returns: list of Paths to extracted files.
    """
    zip_bytes = decrypt_file(ciphertext, key, nonce)

    extracted_files = []
    with ZipFile(io.BytesIO(zip_bytes)) as zipf:
        zipf.extractall(output_dir)
        for name in zipf.namelist():
            extracted_files.append(output_dir / name)

    return extracted_files
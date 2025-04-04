# Ephemeral File Handling

import io
from zipfile import ZipFile
from pathlib import Path
from typing import List
from encryption import encrypt_file, decrypt_file

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
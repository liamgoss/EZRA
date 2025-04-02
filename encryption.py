# AES-252 Encryption
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt_file(file_bytes: bytes) -> dict:
    key = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(12)  # 96 bits for AES-GCM standard
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, file_bytes, None)
    
    return {
        "key": key,
        "nonce": nonce,
        "ciphertext": ciphertext
    }

def decrypt_file(ciphertext: bytes, key: bytes, nonce: bytes) -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)

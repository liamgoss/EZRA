# AES-252 Encryption
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64

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

# --- Master Key Management ---

def get_master_key():
    key_b64 = os.getenv("EZRA_MASTER_KEY")
    if not key_b64:
        raise RuntimeError("EZRA_MASTER_KEY environment variable is not set")
    key = base64.b64decode(key_b64)
    if len(key) != 32:
        raise ValueError("Master key must be 256-bit (32 bytes)")
    return key

# --- EZRM Encryption ---

def encrypt_ezrm(raw_data: bytes) -> bytes:
    key = get_master_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    encrypted = aesgcm.encrypt(nonce, raw_data, None)
    return nonce + encrypted

def decrypt_ezrm(encrypted_data: bytes) -> bytes:
    key = get_master_key()
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
import base64, requests, magic, uuid
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from werkzeug.utils import secure_filename

from utils import generate_proof, pad_base64
from config import SERVER_URL


def download_file(secret_b64: str, logger=print):
    def log(msg):  # nested logger fallback
        if logger:
            logger(msg)

    try:
        secret_bytes = base64.b64decode(pad_base64(secret_b64))
        secret_int = int.from_bytes(secret_bytes, 'big')
        log(f"[✓] Secret decoded into integer: {secret_int}")
    except Exception as e:
        log(f"[!] Invalid base64 secret: {e}")
        return None

    # Step 1: Generate proof
    try:
        log("[⋯] Generating zero-knowledge proof...")
        proof_data = generate_proof(secret_int, logger=logger)
    except Exception as e:
        log(f"[!] Failed to generate proof: {e}")
        return None

    payload = {
        "proof": proof_data["proof"],
        "public": proof_data["public"]
    }

    # Step 2: Send proof to server
    log("[→] Sending proof to server...")
    res = requests.post(f"{SERVER_URL}/download", json=payload)

    if res.status_code != 200:
        log(f"[!] Download failed: {res.status_code} - {res.text}")
        return None

    data = res.json()
    log("[✓] Encrypted file received")

    # Step 3: Decrypt
    try:
        log("[⋯] Decrypting...")
        ciphertext = base64.b64decode(data["ciphertext"])
        nonce = base64.b64decode(data["nonce"])
        key = base64.b64decode(data["key"])[:32]  # Trim padded key if needed
        log(f"nonce: {nonce}")
        key(f"key: {key}")
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        log("[✓] Decryption successful")
    except Exception as e:
        log(f"[!] Decryption failed: {e}")
        return None

    # Step 4: Detect MIME and choose file extension
    mime = magic.from_buffer(plaintext, mime=True)
    ext = {
        "application/pdf": ".pdf",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "application/zip": ".zip",
        "text/plain": ".txt"
    }.get(mime, ".bin")

    output_filename = secure_filename(f"{uuid.uuid4()}{ext}")
    try:
        with open(output_filename, "wb") as f:
            f.write(plaintext)
        log(f"[✓] File saved as: {output_filename} (MIME: {mime})")
        return output_filename
    except Exception as e:
        log(f"[!] Failed to write file: {e}")
        return None


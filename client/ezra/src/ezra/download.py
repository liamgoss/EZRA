import base64, requests, magic, uuid, traceback
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from werkzeug.utils import secure_filename

from ezra.utils import generate_proof, pad_base64
from ezra.config import SERVER_URL


def download_file(secret_b64, dir, logger=print):
    def log(msg):
        if logger:
            logger(msg)

    try:
        composite_bytes = base64.b64decode(pad_base64(secret_b64))
        if len(composite_bytes) != 64:
            log(f"[!] Composite secret must be 64 bytes (32 secret + 32 AES key), got {len(composite_bytes)}")
            return None
        secret_bytes = composite_bytes[:32]
        key_bytes = composite_bytes[32:]

        secret_int = int.from_bytes(secret_bytes, 'big')
        log(f"[✓] Secret parsed and converted to int: {secret_int}")
    except Exception as e:
        log(f"[!] Invalid base64 composite secret: {e}")
        return None

    # Step 1: Generate proof from secret
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

    # Step 2: Send proof and receive file
    log("[→] Sending proof to server...")
    res = requests.post(f"{SERVER_URL}/download", json=payload)

    if res.status_code != 200:
        log(f"[!] Download failed: {res.status_code} - {res.text}")
        return None

    try:
        data = res.json()
        encrypted_bytes = base64.b64decode(data["ciphertext"])
        nonce = encrypted_bytes[:12]
        ciphertext = encrypted_bytes[12:]

        if len(nonce) != 12:
            log(f"[!] Invalid nonce length: {len(nonce)} (expected 12)")
        if len(key_bytes) != 32:
            log(f"[!] Invalid AES key length: {len(key_bytes)} (expected 32)")

        log("[✓] File and nonce received")
    except Exception as e:
        log(f"[!] Failed to parse ciphertext or nonce: {e}")
        return None

    # Step 3: Decrypt
    try:
        log("[⋯] Decrypting file...")
        aesgcm = AESGCM(key_bytes)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        log("[✓] Decryption successful")
    except Exception as e:
        log(f"[!] Decryption failed: {repr(e)}")
        traceback_str = traceback.format_exc()
        log(f"[!] Traceback:\n{traceback_str}")
        return None

    # Step 4: Save decrypted archive (EZRA = encrypted ZIP)
    output_filename = secure_filename(f"{uuid.uuid4()}.zip")
    output_path = f"{dir}/{output_filename}"

    try:
        with open(output_path, "wb") as f:
            f.write(plaintext)
        log(f"[✓] File saved as: {output_path}")
        return output_path
    except Exception as e:
        log(f"[!] Failed to save decrypted archive: {e}")
        return None


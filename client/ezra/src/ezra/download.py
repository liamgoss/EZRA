import base64, requests, magic, uuid, traceback
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from werkzeug.utils import secure_filename

from ezra.utils import generate_proof, pad_base64
from ezra.config import SERVER_URL


def download_file(secret_b64, dir, logger=print):
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
        ciphertext = base64.b64decode(data["ciphertext"]).rstrip(b'\x00')
        nonce = base64.b64decode(data["nonce"])
        if len(nonce) != 12:
            log(f"[!] Warning: Nonce is {len(nonce)} bytes, expected 12")
        key = base64.b64decode(data["key"])
        if len(key) != 32:
            log(f"[!] Warning: AES key is {len(key)} bytes, expected 32")

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        log("[✓] Decryption successful")
    except Exception as e:
        log(f"[!] Decryption failed: {repr(e)}")
        traceback_str = traceback.format_exc()
        log(f"[!] Traceback:\n{traceback_str}")
        return None

    # Step 4: Save as .zip (Once decrypted, .ezra is just a zip file)
    output_filename = secure_filename(f"{uuid.uuid4()}.zip")
    output_path = f"{dir}/{output_filename}"

    try:
        with open(output_path, "wb") as f:
            f.write(plaintext)
        log(f"[✓] File saved as: {output_path}")
        return output_path
    except Exception as e:
        log(f"[!] Failed to write file: {e}")
        return None

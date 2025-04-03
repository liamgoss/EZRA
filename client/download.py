import base64, requests, magic, uuid
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from werkzeug.utils import secure_filename
from config import SERVER_URL


from utils import generate_proof, pad_base64
from config import SERVER_URL

def download_file(secret_b64: str):
    try:
        secret_bytes = base64.b64decode(pad_base64(secret_b64))
        secret_int = int.from_bytes(secret_bytes, 'big')
    except Exception as e:
        print(f"[!] Invalid base64 secret: {e}")
        return

    # Step 1: Generate proof
    try:
        proof_data = generate_proof(secret_int)
    except Exception as e:
        print(f"[!] Failed to generate proof: {e}")
        return

    payload = {
        "proof": proof_data["proof"],
        "public": proof_data["public"]
    }

    # Step 2: Send proof to server
    res = requests.post(f"{SERVER_URL}/download", json=payload)

    if res.status_code != 200:
        print(f"[!] Download failed: {res.status_code} - {res.text}")
        return

    data = res.json()
    ciphertext = base64.b64decode(data["ciphertext"])
    nonce = base64.b64decode(data["nonce"])
    key = base64.b64decode(data["key"])

    # Step 3: Decrypt
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        print("[!] Decryption failed:", e)
        return

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
    with open(output_filename, "wb") as f:
        f.write(plaintext)

    print(f"[+] File decrypted and saved as {output_filename} (MIME: {mime})")
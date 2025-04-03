import base64, requests, magic, uuid
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from werkzeug.utils import secure_filename
from config import SERVER_URL


def download_file(secret_b64: str):
    # Step 1: POST to /download
    res = requests.post(f"{SERVER_URL}/download", json={"secret": secret_b64})
    
    if res.status_code != 200:
        print(f"[!] Failed to download: {res.status_code} - {res.text}")
        return

    data = res.json()
    ciphertext = base64.b64decode(data["ciphertext"])
    nonce = base64.b64decode(data["nonce"])
    key = base64.b64decode(data["key"])

    # Step 2: Decrypt
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        print("[!] Decryption failed:", e)
        return

    # Step 3: Detect MIME
    mime = magic.from_buffer(plaintext, mime=True)
    ext = {
        "application/pdf": ".pdf",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "application/zip": ".zip",
        "text/plain": ".txt"
    }.get(mime, ".bin")

    output_filename = secure_filename(f"{str(uuid.uuid4())}{ext}")
    with open(output_filename, "wb") as f:
        f.write(plaintext)

    print(f"[+] File decrypted and saved as {output_filename} (MIME: {mime})")

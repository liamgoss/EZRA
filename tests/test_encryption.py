from pathlib import Path
import base64
import os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from storage import encrypt_files_to_ezra, decrypt_ezra_to_files

# === ENCRYPT ===
encrypted = encrypt_files_to_ezra([Path("test1.txt"), Path("secret.png")])

with open("test_out.ezra", "wb") as f:
    f.write(encrypted["ciphertext"])

with open("test_out.ezrm", "wb") as f:
    f.write(encrypted["nonce"] + encrypted["key"])

print("Encrypted .ezra and .ezrm written.")
print("Key:", base64.b64encode(encrypted["key"]).decode())
print("Nonce:", base64.b64encode(encrypted["nonce"]).decode())

# === DECRYPT ===
ciphertext = Path("test_out.ezra").read_bytes()
ezrm = Path("test_out.ezrm").read_bytes()
nonce = ezrm[:12]
key = ezrm[12:]

output_dir = Path("recovered")
output_dir.mkdir(exist_ok=True)

extracted_files = decrypt_ezra_to_files(ciphertext, key, nonce, output_dir)

print(f"[✓] Decrypted and extracted {len(extracted_files)} file(s):")
for f in extracted_files:
    print(" -", f.name)

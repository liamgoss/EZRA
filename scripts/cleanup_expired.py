from pathlib import Path
import json, time, os

PROJECT_ROOT = Path("/home/liam/projects/EZRA")
UPLOAD_DIR = PROJECT_ROOT / "uploads"

for ezrd in UPLOAD_DIR.glob("*.ezrd"):
    file_id = ezrd.stem
    try:
        with open(ezrd, "rb") as f:
            raw = f.read().rstrip(b'\x00')
            data = json.loads(raw.decode("utf-8"))
            if time.time() > data.get("expires_at", 0):
                print(f"[!] Expired: {file_id} — deleting...")
                for ext in ["ezra", "ezrm", "ezrd"]:
                    try:
                        (UPLOAD_DIR / f"{file_id}.{ext}").unlink() # Pathlib version of os.remove()
                    except FileNotFoundError:
                        pass
    except Exception as e:
        print(f"[!] Failed to process {ezrd}: {e}")

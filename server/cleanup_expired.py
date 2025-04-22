from pathlib import Path
import time, sqlite3

from paths import UPLOAD_DIR, DB_DIR, TMP_PROOF_PATH, VERIFICATION_KEY_PATH

DB_PATH = DB_DIR / "expirations.db"

# File extensions to delete
EXTS = ["ezra", "proof.json", "public.json"]

now = int(time.time())

# Query expired file_ids
# Should be O(k) where k is expired files
# Not O(1) but better than the O(n) of the previous version
with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.execute("SELECT file_id FROM expirations WHERE expires_at <= ?", (now,))
    expired_ids = [row[0] for row in cursor.fetchall()]

# Remove files + delete DB entries
for file_id in expired_ids:
    print(f"[CLEANUP] Expired: {file_id}")
    for ext in EXTS:
        try:
            (UPLOAD_DIR / f"{file_id}.{ext}").unlink()
        except FileNotFoundError:
            continue
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM expirations WHERE file_id = ?", (file_id,))

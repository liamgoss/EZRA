from pathlib import Path
import sqlite3
from datetime import datetime, timezone

from paths import DB_DIR

def humanize(ts):
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return "Invalid timestamp"

with sqlite3.connect(DB_DIR) as conn:
    cursor = conn.execute("SELECT file_id, expires_at, delete_on_download FROM expirations ORDER BY expires_at ASC")
    rows = cursor.fetchall()

if not rows:
    print("[INFO] No records in database.")
else:
    print(f"[INFO] {len(rows)} expiration records:")
    for file_id, expires_at, delete_flag in rows:
        print(f"• {file_id}")
        print(f"   ├─ Expires: {humanize(expires_at)} (epoch: {expires_at})")
        print(f"   ├─ Delete on Download: {'Yes' if delete_flag else 'No'}")
        

from pathlib import Path

# Base folder (hopefully regardless of where the script is run)
# This should be the root of the project, where the server and related folders are
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Subfolders
SERVER_DIR = PROJECT_ROOT / "server"
UPLOAD_DIR = SERVER_DIR / "uploads"
WORKING_DIR = SERVER_DIR / "working_dir"
LOG_DIR = SERVER_DIR / "logs"
DB_DIR = SERVER_DIR / "db"

# Proof temp files
TMP_PROOF_PATH = WORKING_DIR / "tmp_proof.json"
TMP_PUBLIC_PATH = WORKING_DIR / "tmp_public.json"
VERIFICATION_KEY_PATH = WORKING_DIR / "verification_key.json"


def ensure_directories():
    for path in [UPLOAD_DIR, LOG_DIR, WORKING_DIR]:
        path.mkdir(parents=True, exist_ok=True)
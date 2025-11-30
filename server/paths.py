from pathlib import Path
import os
"""
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname( __file__ ), ".."))
SERVER_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "server"))
UPLOAD_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "uploads"))
LOG_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "logs"))
DB_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "db"))
ARTIFACTS_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "artifacts"))

TMP_PROOF_PATH = os.path.abspath(os.path.join(ARTIFACTS_DIR, "tmp_proof.json"))
TMP_PUBLIC_PATH = os.path.abspath(os.path.join(ARTIFACTS_DIR, "tmp_public.json"))
VERIFICATION_KEY_PATH = os.path.abspath(os.path.join(ARTIFACTS_DIR, "verification_key.json"))
"""
from pathlib import Path

# Root of the project (parent of the file's directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

SERVER_DIR = PROJECT_ROOT / "server"
UPLOAD_DIR = PROJECT_ROOT / "uploads"
LOG_DIR = PROJECT_ROOT / "logs"
DB_DIR = PROJECT_ROOT / "db"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

TMP_PROOF_PATH = ARTIFACTS_DIR / "tmp_proof.json"
TMP_PUBLIC_PATH = ARTIFACTS_DIR / "tmp_public.json"
VERIFICATION_KEY_PATH = ARTIFACTS_DIR / "verification_key.json"


def ensure_directories():
    for path in [UPLOAD_DIR, LOG_DIR, ARTIFACTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)
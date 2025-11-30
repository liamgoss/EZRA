from flask import Flask, render_template, request, jsonify, after_this_request
from storage import timestomp, pad_file_reasonably
from zk_utils import poseidon_hash
from dotenv import load_dotenv
from pathlib import Path
import os, subprocess, base64, json, time, threading, glob, sqlite3, re, datetime
from paths import UPLOAD_DIR, DB_DIR, ensure_directories


load_dotenv()
ensure_directories()
MAX_CONTENT_LENGTH_MB = int(os.getenv("MAX_CONTENT_LENGTH_MB", 275))
MAX_FILE_COUNT = int(os.getenv("MAX_FILE_COUNT", 5))

ARTIFACTS_PATH = input_file = os.path.abspath(os.path.join(os.path.dirname( __file__ ), "..", "artifacts"))

# Ensure the uploads directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

# App config
app = Flask(__name__)
app.config['UPLOAD_DIR'] = UPLOAD_DIR
app.config['DB_DIR'] = DB_DIR
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH_MB * 1000 * 1000 # e.g. 275MB .ezra container size limit
app.config['MAX_FILE_COUNT'] = MAX_FILE_COUNT


@app.errorhandler(413)
def handle_413(e):
    print(f"[!] Payload too large: {e}")

    return "Payload too large. Please ensure your encrypted upload is under {} MB.".format(
        app.config['MAX_CONTENT_LENGTH'] // 1000000
    ), 413




def get_expiration(file_id: str):
    db_path = app.config['DB_DIR'] / "expirations.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT delete_on_download FROM expirations WHERE file_id = ?", (file_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row[0]) if row else False

# HTML pages to be served

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/dmca")
def dmca():
    return render_template("dmca.html")

@app.route("/canary")
def canary():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    canary_path = os.path.join(base_dir, "static/canary/canary.txt.asc")
    with open(canary_path, "r") as f:
        canary_content = f.read()
    
    # Extract the "Last updated" date using regex
    match = re.search(r"Last Updated:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", canary_content)
    if match:
        last_updated = match.group(1).strip()
    else:
        last_updated = "Unknown"  # Fallback if parsing fails
    
    return render_template(
        "canary.html",
        date=last_updated,
        fingerprint="BB9A 9EEA 1443 59DE BB57  9867 8A32 EDA8 0D50 2239",
        public_key_url="/static/canary/ezra_public_key.asc",
        signed_canary_url="/static/canary/canary.txt.asc",
        signature_block=canary_content,
        year=str(datetime.datetime.now(datetime.timezone.utc).year)
    )


# Core EZRA logic

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return "No file provided", 400

    files = request.files.getlist("file")
    if not files or all(f.filename == "" for f in files):
        return "No valid files selected", 400

    if len(files) > MAX_FILE_COUNT:
        return f"Too many files. Maximum allowed is {MAX_FILE_COUNT}.", 400

    # Accept secret for hashing reference only (optional since proof is client-side)
    secret_b64 = request.form.get("secret")
    if not secret_b64:
        return "Missing secret", 400

    try:
        base64.b64decode(secret_b64)
    except Exception:
        return "Invalid base64 secret", 400

    # Get proof and public input from client
    proof_json = request.form.get("zk_proof")
    public_json = request.form.get("zk_public")
    if not proof_json or not public_json:
        return "Missing ZK proof or public input", 400

    try:
        proof = json.loads(proof_json)
        public = json.loads(public_json)
    except Exception:
        return "Invalid proof or public format", 400

    # Use first public input (Poseidon(secret)) as the file_id
    file_id = public[0]

    # Save encrypted file
    f = files[0]
    ezra_path = os.path.join(app.config["UPLOAD_DIR"], f"{file_id}.ezra")
    f.save(ezra_path)

    # Save ZK proof and public signals
    ezrp_proof_path = os.path.join(app.config["UPLOAD_DIR"], f"{file_id}.proof.json")
    ezrp_public_path = os.path.join(app.config["UPLOAD_DIR"], f"{file_id}.public.json")
    with open(ezrp_proof_path, "w") as pf:
        json.dump(proof, pf)
    with open(ezrp_public_path, "w") as pubf:
        json.dump(public, pubf)

    # Handle expiration policy

    expire_hours = int(request.form.get("expire_hours", 24))
    actual_expire = expire_hours if expire_hours > 0 else 24
    delete_after_download = request.form.get("delete_after_download") == "true"
    

    with sqlite3.connect(DB_DIR / "expirations.db") as db:
        db.execute(
            "INSERT OR REPLACE INTO expirations (file_id, expires_at, delete_on_download) VALUES (?, ?, ?)",
            (file_id, int(time.time()) + actual_expire * 3600, int(delete_after_download))
        )


    # Timestomp and pad all relevant files
    pad_file_reasonably(Path(ezra_path))
    timestomp([Path(ezra_path), Path(ezrp_proof_path), Path(ezrp_public_path)])

    print(f"[UPLOAD] Stored file with ID: {file_id}")

    return jsonify({ "file_id": file_id })

@app.route("/poseidon", methods=["POST"])
def poseidon_endpoint():
    data = request.get_json()
    try:
        b64 = data.get("secret_b64")
        if not b64:
            return "Missing input", 400

        binary = base64.b64decode(b64)
        secret = int.from_bytes(binary, byteorder="big")
        hashed = poseidon_hash(secret)
        return jsonify({ "hash": hashed })  # already decimal string
    except Exception as e:
        return f"Error: {str(e)}", 500



def delayed_delete(file_id, delay=120):
    time.sleep(delay)
    try:
        for f in glob.glob(f"{UPLOAD_DIR}/{file_id}.*"):
            os.remove(f)
            print(f"[CLEANUP] Deleted: {f}")
    except Exception as e:
        print(f"[!] Error deleting {file_id}: {e}")
        

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()

    proof = data.get("proof")
    public = data.get("public")

    if not isinstance(proof, dict) or not isinstance(public, list) or not public or not all(isinstance(p, str) for p in public):
        return "Invalid proof/public format", 400

    required_keys = {"pi_a", "pi_b", "pi_c", "protocol", "curve"}
    if not required_keys.issubset(proof.keys()):
        return "Malformed proof structure", 400

    file_id = public[0]

    
    tmp_proof_path = os.path.join(ARTIFACTS_PATH, "tmp_proof.json")
    tmp_public_path = os.path.join(ARTIFACTS_PATH, "tmp_public.json")

    try:
        with open(tmp_proof_path, "w") as pf:
            json.dump(proof, pf)
        with open(tmp_public_path, "w") as pubf:
            json.dump(public, pubf)

        subprocess.run([
            "snarkjs", "groth16", "verify",
            os.path.join(ARTIFACTS_PATH, "verification_key.json" ),
            tmp_public_path,
            tmp_proof_path
        ], check=True)

    except subprocess.CalledProcessError:
        return "Invalid proof", 403
    except Exception as e:
        print(f"Exception during proof verification: {e}")
        return "Server error during proof verification", 500

    ezra_path = os.path.join(UPLOAD_DIR, f"{file_id}.ezra")
    

    if not os.path.exists(ezra_path):
        return "File not found", 404

    should_delete = get_expiration(file_id)
    
    # Load ciphertext before scheduling deletion
    with open(ezra_path, "rb") as f:
        ciphertext = f.read().rstrip(b'\x00')

    if should_delete:
        @after_this_request
        def schedule_deletion(response):
            print(f"[→] Deletion policy active for {file_id} — will delete after response")
            threading.Thread(target=delayed_delete, args=(file_id,), daemon=True).start()
            return response

    return jsonify({
        "ciphertext": base64.b64encode(ciphertext).decode()
    })

    


if __name__ == "__main__":
    # Initialize SQLite database
    # SQLite database setup
    schema = """
    CREATE TABLE IF NOT EXISTS expirations (
        file_id TEXT PRIMARY KEY,
        expires_at INTEGER NOT NULL,
        delete_on_download INTEGER DEFAULT 0
    );
    """
    with sqlite3.connect(DB_DIR / "expirations.db") as db:
        db.execute(schema)
        db.commit()
    print(f"[INIT] Initialized {DB_DIR / 'expirations.db'}")
    app.run(ssl_context="adhoc", host="0.0.0.0", debug=True, port=5001)

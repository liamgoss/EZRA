from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from werkzeug.utils import secure_filename
from pathlib import Path
from zk_utils import generate_secret, poseidon_hash
from storage import encrypt_files_to_ezra, timestomp, pad_file_reasonably, pad_file_to_exact_size
import os, uuid, subprocess, base64, json, time, threading
from dotenv import load_dotenv


load_dotenv()
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads/")
MAX_CONTENT_LENGTH_MB = int(os.getenv("MAX_CONTENT_LENGTH_MB", 50))
MAX_FILE_COUNT = int(os.getenv("MAX_FILE_COUNT", 5))

# Ensure the uploads directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# App config
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH_MB * 1000 * 1000 # e.g. 50MB file size limit
app.config['MAX_FILE_COUNT'] = MAX_FILE_COUNT





@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return "No file provided", 400

    files = request.files.getlist("file")
    if not files or all(f.filename == "" for f in files):
        return "No valid files selected", 400
    
    if len(files) > MAX_FILE_COUNT:
        return f"Too many files. Maximum allowed is {MAX_FILE_COUNT}.", 400

    temp_paths = []
    for f in files:
        original_name = secure_filename(f.filename)
        random_ext = os.path.splitext(original_name)[1]
        random_name = f"{uuid.uuid4()}{random_ext}"
        temp_path = Path("uploads") / random_name
        f.save(temp_path)
        temp_paths.append(temp_path)

    # Create archive + encrypt
    result = encrypt_files_to_ezra(temp_paths)

    # Generate secret + commitment
    secret = generate_secret()
    file_id = poseidon_hash(secret)


    # These will be passed as form data from frontend later
    expire_days = int(request.form.get("expire_days", 7))  # 7 = Default expiration days
    delete_after_download = request.form.get("delete_after_download") == "true" # Convert "true" to Python bool True/False

    # Determine expiration policy
    actual_expire_days = expire_days if expire_days > 0 else 7
    ezrd = {
        "expires_at": int(time.time()) + actual_expire_days * 86400,
        "delete_on_download": delete_after_download or expire_days == 0
    }

    ezra_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{file_id}.ezra") # Encrypted file container
    ezrm_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{file_id}.ezrm") # .ezra decryption key + nonce
    ezrd_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{file_id}.ezrd") # .ezra deletion criteria

    # Save encrypted container to file
    with open(ezra_path, "wb") as f:
        f.write(result["ciphertext"])
    # Save key + nonce
    with open(ezrm_path, "wb") as f:
        f.write(result["nonce"] + result["key"])
    # Save deletion policy
    with open(ezrd_path, "w") as f:
        json.dump(ezrd, f)

    # EZRA container, key/nonce file, and deletion policy file timestomped
    
    pad_file_reasonably(Path(ezra_path)) # Pad .ezra according to next nearest increment
    pad_file_to_exact_size(Path(ezrm_path), 4000) # Pad .ezrm to 4KB
    pad_file_to_exact_size(Path(ezrd_path), 4000) # Pad .ezrd to 4KB
    timestomp([Path(ezra_path), Path(ezrm_path), Path(ezrd_path)])

    print(f"[UPLOAD] Stored file with ID: {file_id}")

    # Cleanup temp files
    for path in temp_paths:
        path.unlink(missing_ok=True)

    # Return base64-encoded secret to the user
    secret_b64 = base64.b64encode(secret.to_bytes(32, "big")).decode()
    return jsonify({ "secret": secret_b64 })


def delayed_delete(file_id, delay=5):
    time.sleep(delay)
    for ext in [".ezra", ".ezrm", ".ezrd"]:
        path = os.path.join(UPLOAD_FOLDER, f"{file_id}{ext}")
        try:
            os.remove(path)
            print(f"[CLEANUP] Deleted: {path}")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[!] Error deleting {path}: {e}")

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    
    proof = data.get("proof")
    public = data.get("public")

    # Validate basic structure
    if not isinstance(proof, dict):
        return "Invalid proof format", 400

    if not isinstance(public, list) or not public or not all(isinstance(p, str) for p in public):
        return "Invalid public format", 400

    # Schema-level validation of the proof object
    required_keys = {"pi_a", "pi_b", "pi_c", "protocol", "curve"}
    if not required_keys.issubset(proof.keys()):
        return "Malformed proof structure", 400

    # Write files for snarkjs to read
    tmp_proof_path = "working_dir/tmp_proof.json"
    tmp_public_path = "working_dir/tmp_public.json"

    try:
        with open(tmp_proof_path, "w") as pf:
            json.dump(proof, pf)

        with open(tmp_public_path, "w") as pubf:
            json.dump(public, pubf)

        # Run snarkjs verify
        subprocess.run([
            "snarkjs", "groth16", "verify",
            "working_dir/verification_key.json",
            tmp_public_path,
            tmp_proof_path
        ], check=True)

    except subprocess.CalledProcessError:
        return "Invalid proof", 403

    except Exception:
        return "Server error during proof verification", 500

    file_id = public[0]
    ezra_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.ezra")
    ezrm_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.ezrm")
    ezrd_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.ezrd")

    print(f"[DOWNLOAD] Looking for: {ezra_path}, {ezrm_path}, {ezrd_path}")

    if not os.path.exists(ezra_path) or not os.path.exists(ezrm_path):
        return "File not found", 404

    # Load .ezrd metadata if it exists
    should_delete = False
    if os.path.exists(ezrd_path):
        with open(ezrd_path, "rb") as f:
            try:
                raw = f.read().rstrip(b'\x00')  # Remove null padding
                ezrd = json.loads(raw.decode("utf-8"))
                should_delete = ezrd.get("delete_on_download", False)
            except Exception as e:
                print(f"[!] Failed to parse .ezrd for {file_id}: {e}")

    if should_delete:
        print(f"[→] Deletion policy active for {file_id} — scheduling deletion in background")
        threading.Thread(target=delayed_delete, args=(file_id,), daemon=True).start()


    with open(ezra_path, "rb") as f:
        ciphertext = f.read()
    with open(ezrm_path, "rb") as f:
        ezrm = f.read()
        nonce = ezrm[:12]
        key = ezrm[12:].rstrip(b"\x00")  # ← Trim padding!

    return jsonify({
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "key": base64.b64encode(key).decode(),
    })

    


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

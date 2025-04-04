from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from werkzeug.utils import secure_filename
from pathlib import Path
from zk_utils import generate_secret, poseidon_hash
from storage import encrypt_files_to_ezra
import os, uuid, subprocess, base64, json

UPLOAD_FOLDER = 'uploads/'


# Ensure the uploads directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1000 * 1000 # 100MB file size limit


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
    from zk_utils import generate_secret, poseidon_hash
    secret = generate_secret()
    file_id = poseidon_hash(secret)

    ezra_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{file_id}.ezra")
    ezrm_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{file_id}.ezrm")

    with open(ezra_path, "wb") as f:
        f.write(result["ciphertext"])
    with open(ezrm_path, "wb") as f:
        f.write(result["nonce"] + result["key"])

    print(f"[UPLOAD] Stored file with ID: {file_id}")

    # Cleanup temp files
    for path in temp_paths:
        path.unlink(missing_ok=True)

    # Return base64-encoded secret to the user
    secret_b64 = base64.b64encode(secret.to_bytes(32, "big")).decode()
    return jsonify({ "secret": secret_b64 })



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

    print(f"[DOWNLOAD] Looking for: {ezra_path}, {ezrm_path}")

    if not os.path.exists(ezra_path) or not os.path.exists(ezrm_path):
        return "File not found", 404

    with open(ezra_path, "rb") as f:
        ciphertext = f.read()
    with open(ezrm_path, "rb") as f:
        ezrm = f.read()
        nonce = ezrm[:12]
        key = ezrm[12:]

    return jsonify({
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "key": base64.b64encode(key).decode(),
    })

    


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

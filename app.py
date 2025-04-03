from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from encryption import encrypt_file
from werkzeug.utils import secure_filename
from zk_utils import generate_secret, poseidon_hash
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
    if 'file' not in request.files:
        return "No file uploaded", 400

    file = request.files['file']
    if file.filename == '':
        return "Empty filename", 400

    # Read file and encrypt
    file_bytes = file.read()
    result = encrypt_file(file_bytes)

    # Generate secret and Poseidon hash (used as file_id)
    secret = generate_secret()
    file_id = poseidon_hash(secret)

    # Store encrypted data
    enc_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.enc")
    meta_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.meta")

    with open(enc_path, "wb") as f:
        f.write(result['ciphertext'])

    with open(meta_path, "wb") as f:
        f.write(result['nonce'] + result['key'])

    # Return the secret (base64 encoded) to the user
    secret_b64 = base64.b64encode(secret.to_bytes(32, 'big')).decode()
    print("Server generated secret (int):", secret)
    print("Base64 returned to client:", secret_b64)

    return jsonify({"secret": secret_b64})



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
    enc_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.enc")
    meta_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.meta")

    if not os.path.exists(enc_path) or not os.path.exists(meta_path):
        return "File not found", 404

    with open(enc_path, "rb") as f:
        ciphertext = f.read()
    with open(meta_path, "rb") as f:
        meta = f.read()
        nonce = meta[:12]
        key = meta[12:]

    return jsonify({
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "key": base64.b64encode(key).decode(),
    })

    


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

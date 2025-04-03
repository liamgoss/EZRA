from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from encryption import encrypt_file
from werkzeug.utils import secure_filename
import os, uuid, subprocess, base64
from zk_utils import generate_secret, poseidon_hash

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
    return jsonify({"secret": secret_b64})


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    secret_b64 = data.get("secret")
    if not secret_b64:
        return "Missing secret", 400

    try:
        secret = int.from_bytes(base64.b64decode(secret_b64), 'big')
    except Exception:
        return "Invalid secret format", 400

    file_id = poseidon_hash(secret)
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


# Placeholder ZK proof endpoint
@app.route("/prove", methods=["POST"])
def generate_proof():
    data = request.get_json()
    secret = data.get("x")

    if not secret:
        return jsonify({"error": "Missing input 'x'"}), 400

    # Write input.json
    input_path = "inputs/input.json"
    os.makedirs(os.path.dirname(input_path), exist_ok=True)
    with open(input_path, "w") as f:
        f.write(f'{{ "x": "{secret}" }}')

    try:
        # Generate witness
        subprocess.run([
            "snarkjs", "wtns", "calculate",
            "circuits/poseidon_preimage_js/poseidon_preimage.wasm",
            input_path,
            "witness.wtns"
        ], check=True)

        # Generate proof
        subprocess.run([
            "snarkjs", "groth16", "prove",
            "circuits/poseidon_preimage_final.zkey",
            "witness.wtns",
            "proof.json",
            "public.json"
        ], check=True)

        # Read output
        with open("proof.json") as pf, open("public.json") as pubf:
            proof = pf.read()
            public = pubf.read()

        return jsonify({
            "success": True,
            "proof": proof,
            "public": public
        })

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Proof generation failed: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

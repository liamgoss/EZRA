from flask import Flask, render_template, request, redirect, url_for, jsonify
import subprocess
import os
from encryption import encrypt_file

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file:
        return "No file provided", 400
    # Handle encryption + storage
    return "File received securely"

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

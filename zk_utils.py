import subprocess
import os
import random
import json

def generate_secret(bits=256):
    return random.getrandbits(bits)

def poseidon_hash(secret: int) -> int:
    # Uses circomlibjs' async Poseidon factory
    script = f"""
    (async () => {{
        const circomlib = require("circomlibjs");
        const poseidon = await circomlib.buildPoseidon();
        const secret = BigInt("{secret}");
        const hash = poseidon.F.toString(poseidon([secret]));
        console.log(hash);
    }})()
    """

    try:
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "NODE_PATH": "./node_modules"}
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        print("Node subprocess failed:")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        raise


def get_commitment(secret: int) -> str:
    input_dir = "inputs"
    input_path = os.path.join(input_dir, "input.json")
    os.makedirs(input_dir, exist_ok=True)

    commitment = poseidon_hash(secret)

    with open(input_path, "w") as f:
        json.dump({ "x": str(secret), "expected": str(commitment) }, f)

    subprocess.run([
        "snarkjs", "wtns", "calculate",
        "working_dir/poseidon_preimage_js/poseidon_preimage.wasm",
        input_path,
        "working_dir/witness.wtns"
    ], check=True)

    subprocess.run([
        "snarkjs", "groth16", "prove",
        "working_dir/poseidon_preimage.zkey",
        "working_dir/witness.wtns",
        "working_dir/proof.json",
        "working_dir/public.json"
    ], check=True)

    return commitment

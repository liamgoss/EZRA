import subprocess
import os
import random
import json

ARTIFACTS_PATH =  os.path.abspath(os.path.join(os.path.dirname( __file__ ), "..", "artifacts"))

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
    input_file = os.path.abspath(os.path.join(ARTIFACTS_PATH, "inputs", "input.json"))
    wasm_file = os.path.abspath(os.path.join(ARTIFACTS_PATH, "poseidon_preimage_js", "poseidon_preimage.wasm"))
    wtns_file = os.path.abspath(os.path.join(ARTIFACTS_PATH, "witness.wtns"))
    
    commitment = poseidon_hash(secret)

    with open(input_file, "w") as f:
        json.dump({ "x": str(secret), "expected": str(commitment) }, f)

    subprocess.run([
        "snarkjs", "wtns", "calculate",
        wasm_file,
        input_file,
        wtns_file,
    ], check=True)

    subprocess.run([
        "snarkjs", "groth16", "prove",
        os.path.join(ARTIFACTS_PATH, "poseidon_preimage.zkey"),
        os.path.join(ARTIFACTS_PATH, "witness.wtns"),
        os.path.join(ARTIFACTS_PATH, "proof.json"),
        os.path.join(ARTIFACTS_PATH, "public.json"),
    ], check=True)

    return commitment

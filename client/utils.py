import os
import json
import subprocess


WORKING_DIR = os.path.join(os.path.dirname(__file__), '..', 'working_dir')


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

def generate_proof(secret: int) -> dict:
    os.makedirs("tmp", exist_ok=True)
    input_path = "tmp/input.json"
    witness_path = "tmp/witness.wtns"
    proof_path = "tmp/proof.json"
    public_path = "tmp/public.json"

    # Compute Poseidon hash as public input
    print(f"Computing poseidon_hash using secret: {secret}")
    commitment = poseidon_hash(secret)
    print(f"Computed commitment: {commitment} from secret: {secret}")

    # Step 1: Write full input.json (x = secret, expected = Poseidon(secret))
    with open(input_path, "w") as f:
        json.dump({"x": str(secret), "expected": str(commitment)}, f)

    # Step 2: Generate witness
    subprocess.run([
        "snarkjs", "wtns", "calculate",
        os.path.join(WORKING_DIR, "poseidon_preimage_js", "poseidon_preimage.wasm"),
        input_path,
        witness_path
    ], check=True)


    # Step 3: Generate proof
    subprocess.run([
        "snarkjs", "groth16", "prove",
        os.path.join(WORKING_DIR, "poseidon_preimage.zkey"),
        witness_path,
        proof_path,
        public_path
    ], check=True)


    

    with open(proof_path, "r") as f:
        proof = json.load(f)
    print(f"Wrote proof to: {proof_path}")
    with open(public_path, "r") as f:
        public = json.load(f)
    print(f"Wrote public to: {public_path}")

    return {
        "proof": proof,
        "public": public
    }

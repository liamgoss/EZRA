import os, sys, json, subprocess, platform


WORKING_DIR = os.path.join(os.path.dirname(__file__), 'working_dir')

def pad_base64(s: str) -> str:
    return s + '=' * (-len(s) % 4)


def get_embedded_node_path():
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))  # Works both dev and packaged
    bin_dir = os.path.join(base, "resources", "node", "bin")

    system = platform.system().lower()
    arch = platform.machine().lower()

    if system == "darwin":
        if arch in ("arm64", "aarch64"):
            return os.path.join(bin_dir, "macos_arm", "node")
        elif arch in ("x86_64", "amd64"):
            return os.path.join(bin_dir, "macos_x64", "node")
    elif system == "linux":
        if arch in ("arm64", "aarch64"):
            return os.path.join(bin_dir, "linux_arm", "node")
        elif arch in ("x86_64", "amd64"):
            return os.path.join(bin_dir, "linux_x64", "node")
    elif system == "windows":
        return os.path.join(bin_dir, "windows", "node.exe")

    raise RuntimeError(f"Unsupported platform or architecture: {system} {arch}")

def get_node_modules_path():
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base, "resources", "node", "node_modules")

def get_snarkjs_path():
    return os.path.join(get_node_modules_path(), "snarkjs", "cli.js")


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
            [get_embedded_node_path(), "-e", script],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "NODE_PATH": get_node_modules_path()}
        )

        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        print("Node subprocess failed:")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        raise

def generate_proof(secret: int, logger=print) -> dict:
    def log(msg):  # nested logger fallback
        if logger:
            logger(msg)

    
    os.makedirs("tmp", exist_ok=True)
    input_path = "tmp/input.json"
    witness_path = "tmp/witness.wtns"
    proof_path = "tmp/proof.json"
    public_path = "tmp/public.json"

    # Compute Poseidon hash as public input
    log(f"Computing poseidon_hash using secret: {secret}")
    commitment = poseidon_hash(secret)
    log(f"Computed commitment: {commitment} from secret: {secret}")

    # Step 1: Write full input.json (x = secret, expected = Poseidon(secret))
    with open(input_path, "w") as f:
        json.dump({"x": str(secret), "expected": str(commitment)}, f)

    # Step 2: Generate witness
    subprocess.run([
        get_embedded_node_path(),
        os.path.join(get_node_modules_path(), "snarkjs", "cli.js"),
        "wtns", "calculate",
        os.path.join(WORKING_DIR, "poseidon_preimage_js", "poseidon_preimage.wasm"),
        input_path,
        witness_path
    ], check=True)


    # Step 3: Generate proof
    subprocess.run([
        get_embedded_node_path(),
        os.path.join(get_node_modules_path(), "snarkjs", "cli.js"),
        "groth16", "prove",
        os.path.join(WORKING_DIR, "poseidon_preimage.zkey"),
        witness_path,
        proof_path,
        public_path
    ], check=True)



    

    with open(proof_path, "r") as f:
        proof = json.load(f)
    log(f"Wrote proof to: {proof_path}")
    with open(public_path, "r") as f:
        public = json.load(f)
    log(f"Wrote public to: {public_path}")

    return {
        "proof": proof,
        "public": public
    }

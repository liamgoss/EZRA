import subprocess
import os
import random
import json

ARTIFACTS_PATH =  os.path.abspath(os.path.join(os.path.dirname( __file__ ), "..", "artifacts"))

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


import subprocess
import json, os, sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tests'))) 
from zk_utils import generate_secret, get_commitment



ARTIFACTS_PATH = os.path.abspath(os.path.join(__file__, "..", "artifacts"))

# 1. Generate a random secret
secret = generate_secret()
print("Secret:", secret)

# 2. Get the corresponding Poseidon commitment hash
commitment = get_commitment(secret)
print("Commitment:", commitment)

# 3. Now verify the proof manually using snarkjs
verify_result = subprocess.run([
    "snarkjs", "groth16", "verify",
    os.path.abspath(os.path.join(ARTIFACTS_PATH, "verification_key.json")),
    os.path.abspath(os.path.join(ARTIFACTS_PATH, "public.json")),
    os.path.abspath(os.path.join(ARTIFACTS_PATH, "proof.json")),
], capture_output=True, text=True)

print("Verifier Output:\n", verify_result.stdout)
print("Verifier Errors:\n", verify_result.stderr)

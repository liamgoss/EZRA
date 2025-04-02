from zk_utils import generate_secret, get_commitment
import subprocess
import json

# 1. Generate a random secret
secret = generate_secret()
print("Secret:", secret)

# 2. Get the corresponding Poseidon commitment hash
commitment = get_commitment(secret)
print("Commitment:", commitment)

# 3. Now verify the proof manually using snarkjs
verify_result = subprocess.run([
    "snarkjs", "groth16", "verify",
    "working_dir/verification_key.json",
    "working_dir/public.json",
    "working_dir/proof.json"
], capture_output=True, text=True)

print("Verifier Output:\n", verify_result.stdout)
print("Verifier Errors:\n", verify_result.stderr)

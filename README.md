# EZRA: Ephemeral Zero-Knowledge Relay Archive

A secure, ephemeral file-sharing prototype using **Zero-Knowledge Proofs** and **AES-256-GCM encryption**. Files are uploaded anonymously, stored encrypted, and can only be retrieved by proving knowledge of a secret (preimage) without revealing it.

This project uses **Circom 2.1.6** and **snarkjs** (Groth16) to implement a Poseidon preimage proof, and avoids blockchain dependencies entirely.

---

## Prerequisites

Install the following:
- [Rust](https://rustup.rs) (for building Circom)
- Node.js + npm
- `snarkjs`: `npm install  snarkjs`
- `circomlibjs`: `npm install  circomlibjs`
- Circom 2.1.6 (build from source): https://github.com/iden3/circom

Inside your project root:
```bash
npm init -y
npm install circomlibjs
npm install snarkjs
```

---

## Project Structure (Simplified)

```bash
EZRA/
├── circuits                       # Circom circuit files
│   ├── poseidon.circom
│   ├── poseidon_constants.circom
│   └── poseidon_preimage.circom
├── scripts
│   └── build_zk.sh                # Rebuild working_dir from source
├── working_dir                    # Circuit build output (auto-generated)
│   ├── poseidon_preimage_js
│   │   ├── generate_witness.js
│   │   ├── poseidon_preimage.wasm
│   │   └── witness_calculator.js
│   ├── poseidon_preimage.r1cs
│   ├── poseidon_preimage.sym
│   ├── poseidon_preimage.zkey
│   ├── pot12_final.ptau
│   ├── proof.json
│   ├── public.json
│   ├── verification_key.json
│   └── witness.wtns
├── app.py                        # Flask App
├── encryption.py                 # AES-GCM file encryption
└── zk_utils.py                   # Circom+snarkjs interop
```

---

## Build the ZK Circuit

To build all proving/verification artifacts:
```bash
./scripts/build_zk.sh
```
This will:
- Compile the circuit
- Generate proving and verification keys
- Download `pot12_final.ptau` if needed
- Place everything in `working_dir/`

---

## Manual ZK Proof Test

To manually test proof generation:
```bash
python3 zk_test.py
```
This script will:
1. Generate a random secret `s`
2. Compute `h = Poseidon(s)`
3. Create a ZK proof that you know `s` such that `Poseidon(s) = h`
4. Verify that proof using `snarkjs`

Expected output:
```
Secret: 123...
Commitment: 456...
Verifier Output:
 [INFO]  snarkJS: OK!
```

---

## Alice & Bob Example

### Alice uploads a file:
- The EZRA server:
  - Generates a random secret `s`
  - Computes `h = Poseidon(s)`
  - Encrypts Alice's file using AES-256-GCM
  - Stores the file as `uploads/h.bin`
  - Returns `s` to Alice

### Bob downloads the file:
- Alice gives Bob the secret `s` (securely, out-of-band)
- Bob uses the EZRA client or tool to:
  - Generate a ZK proof that he knows `s` such that `Poseidon(s) = h`
  - Send the proof + public commitment to the EZRA server
  - If valid, the server sends back the encrypted file
  - Bob decrypts it locally using `s` or a derived AES key

This achieves:
- Anonymous file delivery
- No metadata or identifiers stored
- Zero-Knowledge access control
- One-time access if desired

---

## Files Summary

| File | Purpose |
|------|---------|
| `poseidon_preimage.circom` | Circuit: prove knowledge of secret `s` s.t. `Poseidon(s) = h` |
| `build_zk.sh` | Automates compiling, setup, and key generation |
| `witness.wtns` | Witness generated for specific inputs |
| `proof.json` | Proof that `s` is the preimage of `h` |
| `public.json` | Public inputs (contains `h`) |
| `verification_key.json` | For verifying ZK proof |
| `uploads/<h>.bin` | Encrypted file stored by EZRA |

---

## Coming Soon

- `ezra-client`: minimal multiplatform tool to prove + download
- `/download` route for server-side verification
- Enterprise mode (configurable logging, multiple recipients)

---

> Security through math. Privacy by default. Welcome to your digital dead drop.


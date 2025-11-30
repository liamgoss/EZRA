# EZRA: Ephemeral Zero-Knowledge Relay Archive

A secure, ephemeral file-sharing prototype using **Zero-Knowledge Proofs** and **AES-256-GCM encryption**. Files are uploaded anonymously, stored encrypted, and can only be retrieved by proving knowledge of a secret (preimage) without revealing it.

This project uses **Circom 2.1.6** and **snarkjs** (Groth16) to implement a Poseidon preimage proof, and avoids blockchain dependencies entirely.

---

## Prerequisites

Install the following:
- [Rust](https://rustup.rs) (for building Circom)
- Node.js + npm
- `snarkjs`: `npm install snarkjs`
- `circomlibjs`: `npm install circomlibjs`
- Circom 2.1.6 (build from source): https://github.com/iden3/circom

Inside your project root:
```bash
npm init -y
npm install circomlibjs
npm install snarkjs
```

> NOTE: All JavaScript dependencies for ZK circuit building and proof generation (e.g. snarkjs, circomlibjs) are managed via the root-level package.json.

## Project Structure (Simplified)
```
EZRA/
├── circuits/                     # Circom circuit files
│   ├── poseidon.circom
│   ├── poseidon_constants.circom
│   └── poseidon_preimage.circom
├── client/                       # GUI + CLI client tool
│   ├── ezra.py
│   ├── gui.py
│   ├── download.py
│   ├── utils.py
│   ├── config.py
│   ├── tmp/                      # Temporary input/proof files
│   └── working_dir/             # ZK artifacts copied here during build
├── server/                       # Flask web server
│   ├── app.py
│   ├── encryption.py
│   ├── storage.py
│   ├── zk_utils.py
│   ├── templates/
│   ├── static/
│   ├── uploads/                 # Encrypted file storage
│   ├── working_dir/            # ZK artifacts used at runtime
│   ├── scripts/
│   │   ├── cleanup_expired.py  # Deletes expired uploads
│   └── requirements.txt
├── tests/                        # Test suite
│   ├── test_routes.py
│   ├── test_storage.py
│   ├── test_zk_utils.py
│   └── test_encryption.py
├── build_zk.sh                   # Builds ZK artifacts and syncs them to server/ + client/
├── README.md
└── .gitignore
```

## .env Configuration
The Flask server requires a `.env` file located at `server/.env`. A template is provided:

```bash
cp server/env.example server/.env
```

Edit the `.env` file and set your master key:

```bash
EZRA_MASTER_KEY=your-256-bit-hex-key
```

This key is used for AES-GCM file encryption. Make sure it is a valid 32-byte (256-bit) hex string.

## Build the ZK Circuit
From the project root, run:

```bash
chmod +x build_zk.sh && ./build_zk.sh
```

This will:

- Compile the Circom circuit
- Download `pot12_final.ptau` if missing
- Generate proving and verification keys
- Copy the resulting artifacts into both:
  
  - `server/working_dir/`
  - `client/working_dir/`

These artifacts are required for both uploading and downloading files.

## Manual ZK Proof Test
To manually test ZK proof generation and verification:

```bash
cd server && python3 zk_test.py
```
Expected output (secret and commitment values may differ from the following):
```yaml
Secret: 391279... 
Commitment: 126827...
Verifier Output: OK!
```

## Alice & Bob Example
### Alice uploads a file:
- The EZRA server:
  - Generates a random secret `s`
  - Compute h = Poseidon(s)
  - Encrypts Alice's file using AES-256-GCM
  - Stores the file as `uploads/<h>.ezra`
  - Returns `s` to Alice

### Bob downloads the file:
- Alice gives Bob the secret `s` securely (out-of-band e.g. via Signal)
- Bob uses the EZRA client tool to:
  - Generate a ZK proof that he knows `s` such that `Poseidon(s)=h`
  - Send the proof + public commitment to the server
  - If valid, the server returns the encrypted file and deletes it from the server
  - The client tool decrypts the encrypted file, converts to `<UUID>.zip`


This achieves:
- Anonymous file delivery
- No metadata or identity stored
- Zero-Knowledge access verification
- One-time file access (optional)


## Testing
From the project root, run:
```bash
PYTHONPATH=server coverage run -m unittest discover -s tests -p "test_*.py"
coverage report
coverage html
```

To test encryption functions, make sure `server/.env` exists and `EZRA_MASTER_KEY` is set

## Scripts
`build_zk.sh`

Located at the root. Builds the circuit and populates both server and client `working_dir/` directories.

`server/scripts/cleanup_expired.py`

Deletes expired `.ezra`,`.ezrm`, and `.ezrd` files from `uploads/`. Be sure to update the directory path before using in production:
```python
# inside cleanup_expired.py
from pathlib import Path

PROJECT_ROOT = Path("/home/liam/projects/EZRA")
UPLOAD_DIR = PROJECT_ROOT / "server" / "uploads"
```
You may want to modify this path dynamically using `__file__` if deploying across systems.

## Files Summary
| File                   | Purpose                                                             |
|------------------------|---------------------------------------------------------------------|
| `poseidon_preimage.circom` | Circuit: prove knowledge of secret s such that Poseidon(s) = h    |
| `build_zk.sh`            | Automates compiling, setup, and key distribution                   |
| `witness.wtns`           | Witness generated for specific inputs                              |
| `proof.json`             | Proof that s is the preimage of h                                  |
| `public.json`            | Public inputs (contains h)                                         |
| `verification_key.json`  | For verifying ZK proof                                              |
| `uploads/<h>.ezra`       | Encrypted file stored by EZRA server                               |
| `.env`                   | Contains EZRA_MASTER_KEY for AES-GCM encryption                    |


## Coming Soon
- Enterprise mode with RBAC and optional audit logging

- File expiration and one-time download support

- Auto-extract ZIP archives on client

- Client packaging as binary app (Briefcase or PyInstaller)

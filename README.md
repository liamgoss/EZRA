# EZRA: Ephemeral Zero-Knowledge Relay Archive

A secure, ephemeral file-sharing system using client-side Zero-Knowledge Proofs and browser-based AES-256-GCM encryption. Files are uploaded anonymously, stored encrypted, and can only be retrieved by proving knowledge of a secret (preimage) without revealing it.

This project uses Circom 2.1.6 and snarkjs (Groth16) for client-side Poseidon preimage proofs, with all encryption and proof generation happening in the browser.

---

---

## SECURITY NOTICE / 
EZRA’s zero-knowledge proof system relies on a publicly available universal trusted setup (Powers of Tau) generated via a multi-party computation (MPC) ceremony.
Security of the ZKP components assumes that at least one participant in the ceremony destroyed their secret randomness.

The project **does not conduct its own ceremony** and instead reuses widely trusted, publicly verifiable parameters.
While this trust model is standard for modern SNARK systems, EZRA’s ZKP integration should still be considered experimental pending further audit, formal verification, and adversarial testing.
---

---

## Key Features

- End-to-End Encryption: Files encrypted in browser with AES-256-GCM
- Zero-Knowledge Proofs: Prove you know the secret without revealing it
- Fully Browser-Based: No client installation required
- Ephemeral Storage: Configurable expiration (1-72 hours)
- One-Time Downloads: Optional delete-after-download
- Privacy-First: Timestomping and file padding for metadata protection

---

## Prerequisites

Install the following on your server:

- Python 3.8+
- Node.js + npm
- Rust (for building Circom from source)
- Circom 2.1.6: https://github.com/iden3/circom
- snarkjs CLI: `npm install -g snarkjs`

Inside your project root:

```bash
npm init -y
npm install circomlibjs
npm install snarkjs
```

> NOTE: JavaScript dependencies (snarkjs, circomlibjs) are used server-side only for the Poseidon hash helper endpoint. All ZK proof generation happens client-side in the browser.

---

## Project Structure

```
EZRA/
├── circuits/                     # Circom circuit files
│   ├── poseidon.circom
│   ├── poseidon_constants.circom
│   └── poseidon_preimage.circom
├── server/                       # Flask web server
│   ├── app.py                    # Main Flask application
│   ├── storage.py                # File padding and timestomping
│   ├── zk_utils.py               # Poseidon hash helper
│   ├── paths.py                  # Directory configuration
│   ├── templates/                # HTML templates
│   ├── static/                   # Frontend assets
│   │   ├── file_logic.js         # Upload/download handlers
│   │   ├── zkp_logic.js          # Client-side ZK proof generation
│   │   ├── modal_logic.js        # UI modals
│   │   ├── style.css
│   │   ├── poseidon_preimage.wasm  # ZK circuit (client-side)
│   │   ├── poseidon_preimage.zkey  # Proving key (client-side)
│   │   └── canary/               # Warrant canary files
│   ├── uploads/                  # Encrypted file storage
│   ├── db/                       # SQLite expiration database
│   └── requirements.txt
├── artifacts/                    # ZK verification artifacts
│   └── verification_key.json     # Server-side proof verification
├── tests/                        # Test suite
│   ├── test_routes.py
│   ├── test_storage.py
│   └── test_zk_utils.py
├── build_zk.sh                   # Builds ZK artifacts
├── README.md
└── .gitignore
```

---

## Setup Instructions

### 1. Build the ZK Circuit

From the project root, run:

```bash
chmod +x build_zk.sh && ./build_zk.sh
```

This will:
- Download `pot12_final.ptau` if missing
- Compile the Circom circuit
- Generate proving key (`.zkey`) and verification key
- Copy artifacts to:
  - `server/static/` (for client-side proving)
  - `artifacts/` (for server-side verification)

### 2. Install Python Dependencies

```bash
cd server
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Server

```bash
cd server
python app.py
```

The server will start on `https://localhost:5001` (uses ad-hoc SSL).

---

## How It Works

### Upload Flow

1. **User selects files** in browser
2. **Client-side processing**:
   - Files are zipped using JSZip
   - Random 32-byte `secret` and 32-byte `aesKey` are generated
   - Files encrypted with AES-GCM using `aesKey`
   - ZK proof generated: "I know `secret` such that `Poseidon(secret) = hash`"
   - Proof uses `.wasm` and `.zkey` files downloaded from server
3. **Upload to server**:
   - Encrypted file (`.ezra`)
   - ZK proof and public signals (the hash)
   - Expiration settings
4. **Server stores**:
   - File ID = `Poseidon(secret)`
   - Saves `.ezra`, `.proof.json`, `.public.json`
   - Records expiration in SQLite database
5. **User receives composite key**: `secret + aesKey` (base64-encoded)

### Download Flow

1. **User enters composite key** (received from uploader)
2. **Client-side processing**:
   - Split key into `secret` and `aesKey`
   - Generate ZK proof: "I know `secret` such that `Poseidon(secret) = hash`"
3. **Send proof to server**
4. **Server verifies proof**:
   - Uses snarkjs CLI to verify proof against `verification_key.json`
   - If valid, returns encrypted `.ezra` file
   - Optionally deletes file if "delete after download" was set
5. **Client-side decryption**:
   - Decrypt with `aesKey` using AES-GCM
   - Unzip files and trigger download

### Security Properties

- **Anonymous**: No user accounts or authentication
- **Zero-Knowledge**: Server never sees the secret, only proofs
- **End-to-End Encrypted**: Server cannot decrypt files
- **Ephemeral**: Files auto-expire after configured time
- **Metadata Protection**: Files are timestomped (epoch time) and padded to obfuscate size

---

## Alice & Bob Example

### Alice uploads a file:

1. Opens EZRA website
2. Selects file, sets expiration to 24 hours
3. Browser encrypts file and generates ZK proof
4. Receives composite key: `dGVzdF9zZWNyZXRfMzJfYnl0ZXNfaGVyZV9f...`

### Bob downloads the file:

1. Alice sends Bob the composite key via Signal (out-of-band)
2. Bob opens EZRA website, enters the key
3. Browser generates ZK proof from the key
4. Server verifies proof and returns encrypted file
5. Browser decrypts and downloads `ezra_files.zip`

This achieves:
- Anonymous file delivery
- No metadata or identity stored
- Zero-Knowledge access verification
- One-time file access (optional)

---

## Testing

From the project root:

```bash
cd server
source venv/bin/activate
pytest tests/ -v
```

For coverage report:

```bash
coverage run -m pytest tests/
coverage report
coverage html
```

---

## API Endpoints

### `POST /upload`
Upload encrypted file with ZK proof.

**Form Data:**
- `file`: Encrypted file (`.ezra`)
- `secret`: Base64-encoded secret (32 bytes)
- `zk_proof`: JSON proof object
- `zk_public`: JSON public signals array
- `expire_hours`: Expiration time (1-72)
- `delete_after_download`: Boolean flag

**Returns:** `{ "file_id": "..." }`

### `POST /download`
Download file by proving knowledge of secret.

**JSON Body:**
```json
{
  "proof": { "pi_a": [...], "pi_b": [...], "pi_c": [...], "protocol": "groth16", "curve": "bn128" },
  "public": ["<file_id>"]
}
```

**Returns:** `{ "ciphertext": "base64..." }`

### `POST /poseidon`
Helper endpoint to compute Poseidon hash (used by client).

**JSON Body:**
```json
{
  "secret_b64": "base64-encoded-secret"
}
```

**Returns:** `{ "hash": "decimal_string" }`

---

## Maintenance Scripts

### Cleanup Expired Files

```bash
cd server
python cleanup_expired.py
```

Set up a cron job to run this periodically:

```bash
0 * * * * cd /path/to/EZRA/server && python cleanup_expired.py
```

---

## File Artifacts Summary

| File                       | Purpose                                                     | Location           |
|----------------------------|-------------------------------------------------------------|--------------------|
| `poseidon_preimage.circom` | Circuit proving knowledge of Poseidon preimage              | `circuits/`        |
| `poseidon_preimage.wasm`   | Compiled circuit for browser-based proof generation         | `server/static/`   |
| `poseidon_preimage.zkey`   | Proving key for client-side ZK proof generation             | `server/static/`   |
| `verification_key.json`    | Verification key for server-side proof verification         | `artifacts/`       |
| `<file_id>.ezra`           | Encrypted file blob                                         | `server/uploads/`  |
| `<file_id>.proof.json`     | ZK proof stored with upload                                 | `server/uploads/`  |
| `<file_id>.public.json`    | Public signals (commitment/hash)                            | `server/uploads/`  |
| `expirations.db`           | SQLite database tracking file expiration                    | `server/db/`       |

---

## Security Considerations

- The `.zkey` proving key is public by design (needed for client-side proving)
- The composite key must be transmitted securely (Signal, encrypted email, etc.)
- Server verification ensures only users with the correct secret can download
- File padding and timestomping provide additional metadata privacy
- One-time download option prevents key reuse

---

## License

AGPL v3 - see LICENSE file for details

For commercial licensing options (private deployment without AGPL obligations), contact Liam Goss at liamjgoss+ezra@gmail.com

---

## Contributing

Contributions welcome! Please open an issue or PR on GitHub.

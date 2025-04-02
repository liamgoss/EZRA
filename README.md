# Poseidon Preimage ZK Proof Example (Circom 2 + snarkjs)

This project demonstrates how to create a Zero-Knowledge Proof in Circom 2 for validating knowledge of a preimage to a Poseidon hash. The proof is non-interactive and compatible with the Groth16 proving system. This setup avoids blockchain dependencies and is fully local.

## Prerequisites

Install the following tools:

- Rust (for building Circom): https://rustup.rs
- Node.js and npm
- snarkjs (`npm install -g snarkjs`)
- Circom 2.1.6 (build from source): https://github.com/iden3/circom

## Directory Setup

```
mkdir ~/projects/poseidon-preimage-test
cd ~/projects/poseidon-preimage-test
```

## Install circomlib

```
npm init -y
npm install circomlib
```

## Circuit: poseidon_preimage.circom

Create a file named `poseidon_preimage.circom` with the following contents:

```circom
include "circomlib/poseidon.circom";

template PoseidonPreimage() {
    signal input x;
    signal output hash;

    component hasher = Poseidon(1);
    hasher.inputs[0] <== x;
    hash <== hasher.out;
}

component main = PoseidonPreimage();
```

## Compile the Circuit

This generates the constraint system, the witness generation code, and the symbol file.

```
circom poseidon_preimage.circom --r1cs --wasm --sym
```

Expected output:
- poseidon_preimage.r1cs
- poseidon_preimage.sym
- poseidon_preimage_js/ (contains .wasm and witness_calculator.js)

## Create Input File

Make an input file to use for witness generation:

`input.json`
```json
{
  "x": "123456789"
}
```

## Generate Witness

Option A: Using snarkjs directly (preferred)

```
snarkjs wtns calculate poseidon_preimage_js/poseidon_preimage.wasm input.json witness.wtns
```

Option B: Using a custom script with witness_calculator.js (if needed)

```js
// make_witness.js
const wc = require('./poseidon_preimage_js/witness_calculator.js');
const fs = require('fs');
const wasm = fs.readFileSync('./poseidon_preimage_js/poseidon_preimage.wasm');

async function run() {
    const input = JSON.parse(fs.readFileSync('./input.json'));
    const witnessCalculator = await wc(builder => builder(wasm));
    const witness = await witnessCalculator.calculateWTNSBin(input, 0);
    fs.writeFileSync('witness.wtns', witness);
}

run();
```

Run it:

```
node make_witness.js
```

## Trusted Setup (Groth16)

### Step 1: Generate initial Powers of Tau file

```
snarkjs powersoftau new bn128 12 pot12_0000.ptau -v
```

### Step 2: Contribute randomness

```
snarkjs powersoftau contribute pot12_0000.ptau pot12_final.ptau --name="EZRA Dev" -v
```

### Step 3: Prepare for phase 2

```
snarkjs powersoftau prepare phase2 pot12_final.ptau pot12_final_prepared.ptau
```

### Step 4: Generate initial zkey from R1CS and PTAU

```
snarkjs groth16 setup poseidon_preimage.r1cs pot12_final_prepared.ptau poseidon_preimage_0000.zkey
```

### Step 5: Contribute to zkey phase 2

```
snarkjs zkey contribute poseidon_preimage_0000.zkey poseidon_preimage_final.zkey --name="EZRA Phase 2"
```

### Step 6: Export verification key

```
snarkjs zkey export verificationkey poseidon_preimage_final.zkey verification_key.json
```

## Generate and Verify Proof

### Step 1: Generate proof

```
snarkjs groth16 prove poseidon_preimage_final.zkey witness.wtns proof.json public.json
```

### Step 2: Verify proof

```
snarkjs groth16 verify verification_key.json public.json proof.json
```

Expected output:
```
OK
```

## Files Summary

- `poseidon_preimage.circom` – Circom 2 circuit definition
- `input.json` – Input to the circuit
- `witness.wtns` – Binary witness file
- `proof.json` – Proof output
- `public.json` – Public outputs (e.g., the Poseidon hash)
- `poseidon_preimage_final.zkey` – Final proving key
- `verification_key.json` – For verifying the proof


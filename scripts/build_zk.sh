#!/bin/bash
set -e  # Exit on any error

# Circuit settings
CIRCUIT_NAME=poseidon_preimage
CIRCUIT_DIR=circuits
WORKING_DIR=working_dir
POT=$WORKING_DIR/pot12_final.ptau

mkdir -p $WORKING_DIR
mkdir -p $CIRCUIT_DIR

# 1. Download ptau if not already present
if [ ! -f $POT ]; then
  echo "Downloading pot12_final.ptau..."
  wget https://storage.googleapis.com/zkevm/ptau/powersOfTau28_hez_final_12.ptau -O $POT
else
  echo "Using existing pot12_final.ptau"
fi

# 2. Compile circuit (with include path)
echo "Compiling $CIRCUIT_NAME..."
circom $CIRCUIT_DIR/$CIRCUIT_NAME.circom \
  --r1cs \
  --wasm \
  --sym \
  -o $WORKING_DIR \
  -l $CIRCUIT_DIR

# 3. Generate zkey
echo "Generating zkey..."
snarkjs groth16 setup \
  $WORKING_DIR/$CIRCUIT_NAME.r1cs \
  $POT \
  $WORKING_DIR/$CIRCUIT_NAME.zkey

# 4. Export verification key
echo "Exporting verification key..."
snarkjs zkey export verificationkey \
  $WORKING_DIR/$CIRCUIT_NAME.zkey \
  $WORKING_DIR/verification_key.json

echo "Build complete. Artifacts in $WORKING_DIR/"

#!/bin/bash
set -e  # Exit on any error

# Circuit settings
CIRCUIT_NAME=poseidon_preimage
CIRCUIT_DIR=circuits
BUILD_DIR=build/working_dir
POT=$BUILD_DIR/pot12_final.ptau

mkdir -p $BUILD_DIR
mkdir -p $CIRCUIT_DIR

# 1. Download ptau if not already present
if [ ! -f $POT ]; then
  echo "Downloading pot12_final.ptau..."
  wget https://storage.googleapis.com/zkevm/ptau/powersOfTau28_hez_final_12.ptau -O $POT
else
  echo "Using existing pot12_final.ptau"
fi

# 2. Compile circuit
echo "Compiling $CIRCUIT_NAME..."
circom $CIRCUIT_DIR/$CIRCUIT_NAME.circom \
  --r1cs --wasm --sym -o $BUILD_DIR -l $CIRCUIT_DIR

# 3. Generate zkey
echo "Generating zkey..."
snarkjs groth16 setup \
  $BUILD_DIR/$CIRCUIT_NAME.r1cs \
  $POT \
  $BUILD_DIR/$CIRCUIT_NAME.zkey

# 4. Export verification key
echo "Exporting verification key..."
snarkjs zkey export verificationkey \
  $BUILD_DIR/$CIRCUIT_NAME.zkey \
  $BUILD_DIR/verification_key.json

# 5. Copy artifacts to server/static/ and artifacts/
echo "Copying frontend artifacts to server/static/"
mkdir -p server/static
cp "$BUILD_DIR/poseidon_preimage.wasm" server/static/
cp "$BUILD_DIR/poseidon_preimage.zkey" server/static/

echo "Copying backend verification key to artifacts/"
mkdir -p artifacts
cp "$BUILD_DIR/verification_key.json" artifacts/
cp "$BUILD_DIR/poseidon_preimage.zkey" artifacts/

echo "Build complete and distributed to server/"
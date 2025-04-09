#!/bin/bash
set -e

VERSION="v23.11.0"
BASE_URL="https://nodejs.org/dist/${VERSION}"
DEST_BASE="client/ezra/src/ezra/resources/node"
BIN_DIR="${DEST_BASE}/bin"
NODE_MODULES_DIR="${DEST_BASE}/node_modules"

# Detect OS and arch
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Darwin)
        platform="darwin"
        if [[ "$ARCH" == "arm64" ]]; then
            arch="arm64"
            dest_subdir="macos_arm"
        else
            arch="x64"
            dest_subdir="macos_x64"
        fi
        ext="tar.gz"
        ;;
    Linux)
        platform="linux"
        if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
            arch="arm64"
            dest_subdir="linux_arm"
        else
            arch="x64"
            dest_subdir="linux_x64"
        fi
        ext="tar.xz"
        ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
        platform="win"
        arch="x64"
        dest_subdir="windows"
        ext="zip"
        ;;
    *)
        echo "Unsupported platform: $OS"
        exit 1
        ;;
esac

FILENAME="node-${VERSION}-${platform}-${arch}.${ext}"
URL="${BASE_URL}/${FILENAME}"
TEMP_DIR="scripts/tmp_node_dl"
mkdir -p "$TEMP_DIR"

echo "Downloading $FILENAME from $URL..."
curl -L "$URL" -o "${TEMP_DIR}/${FILENAME}"

echo "Extracting..."
case "$ext" in
    tar.gz)
        tar -xzf "${TEMP_DIR}/${FILENAME}" -C "$TEMP_DIR"
        ;;
    tar.xz)
        tar -xJf "${TEMP_DIR}/${FILENAME}" -C "$TEMP_DIR"
        ;;
    zip)
        unzip -q "${TEMP_DIR}/${FILENAME}" -d "$TEMP_DIR"
        ;;
esac

EXTRACTED_DIR="${TEMP_DIR}/node-${VERSION}-${platform}-${arch}"
mkdir -p "${BIN_DIR}/${dest_subdir}"

if [[ "$platform" == "win" ]]; then
    cp "${EXTRACTED_DIR}/node.exe" "${BIN_DIR}/${dest_subdir}/node.exe"
else
    cp "${EXTRACTED_DIR}/bin/node" "${BIN_DIR}/${dest_subdir}/node"
    chmod +x "${BIN_DIR}/${dest_subdir}/node"
fi

echo "Node binary placed in ${BIN_DIR}/${dest_subdir}/"

# Install circomlibjs once into node_modules
if [[ ! -d "${NODE_MODULES_DIR}/circomlibjs" ]]; then
    echo "📦 Installing circomlibjs into ${NODE_MODULES_DIR}..."
    npm install --prefix "${DEST_BASE}" circomlibjs
else
    echo "circomlibjs already installed."
fi

# Install snarkjs once into node_modules
if [[ ! -d "${NODE_MODULES_DIR}/snarkjs" ]]; then
    echo "Installing snarkjs into ${NODE_MODULES_DIR}..."
    npm install --prefix "${DEST_BASE}" snarkjs
else
    echo "snarkjs already installed."
fi

# Clean up
rm -rf "$TEMP_DIR"
echo "Done!"

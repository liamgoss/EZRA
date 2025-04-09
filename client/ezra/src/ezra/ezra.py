import argparse, base64, json, os, inspect, sys

from ezra.download import download_file
from ezra.utils import generate_proof, pad_base64


def main():
    parser = argparse.ArgumentParser(description="EZRA Zero-Knowledge Client")
    subparsers = parser.add_subparsers(dest="command")

    # Download
    download = subparsers.add_parser("download", help="Download a file using a secret")
    download.add_argument("secret", help="Base64 secret provided to you")

    # Generate Proof
    #download = subparsers.add_parser("generate", help="Generate a Zero-Knowledge Proof using a given secret")
    #download.add_argument("secret", help="Base64 secret provided to you")

    args = parser.parse_args()

    if args.command == "download":
        download_file(args.secret)
    #elif args.command == "generate":
    #    padded = pad_base64(args.secret)
    #    secret_bytes = base64.b64decode(padded)
    #    secret_int = int.from_bytes(secret_bytes, 'big')
    #    print("Client received base64:", args.secret)
    #    print("Decoded secret (int):", secret_int)
    #    proof_data = generate_proof(secret_int)
    #    print("Proof:", proof_data["proof"])
    #    print("Public:", proof_data["public"])  # Should be poseidon(s)
    #    
        """
        with open("proof.json", "w") as f:
            json.dump(proof_data["proof"], f, indent=2)

        with open("public.json", "w") as f:
            json.dump(proof_data["public"], f, indent=2)
        """
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
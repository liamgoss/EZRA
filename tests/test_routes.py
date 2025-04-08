import unittest
import tempfile
import os
import json
import shutil
import subprocess
from unittest.mock import patch, MagicMock
from app import app, UPLOAD_FOLDER, delayed_delete
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from encryption import get_master_key, encrypt_ezrm
from pathlib import Path

class FlaskRouteTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["DEBUG"] = True  # Show full errors
        self.client = app.test_client()
        self.test_file = tempfile.NamedTemporaryFile(delete=False)
        self.test_file.write(b"Test content for upload")
        self.test_file.close()

        # Create working_dir used by proof system
        os.makedirs("working_dir", exist_ok=True)
        with open("working_dir/proof.json", "w") as f:
            json.dump({}, f)
        with open("working_dir/public.json", "w") as f:
            json.dump(["test"], f)
        with open("working_dir/verification_key.json", "w") as f:
            f.write("dummy key")
        
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    def tearDown(self):
        os.unlink(self.test_file.name)

        if os.path.exists(UPLOAD_FOLDER):
            for file in os.listdir(UPLOAD_FOLDER):
                file_path = os.path.join(UPLOAD_FOLDER, file)
                if os.path.basename(file_path) != ".gitkeep":
                    os.unlink(file_path)

        # Remove working_dir completely
        shutil.rmtree("working_dir", ignore_errors=True)

    @patch("app.encrypt_files_to_ezra")
    @patch("app.generate_secret")
    @patch("app.get_commitment")
    @patch("app.encrypt_ezrm")
    def test_upload_success(self, mock_enc_ezrm, mock_commitment, mock_secret, mock_encrypt):
        mock_secret.return_value = 123456789
        mock_commitment.return_value = "mock_id"
        mock_enc_ezrm.return_value = b"dummy_ezrm"
        mock_encrypt.return_value = {"ciphertext": b"cipher", "key": b"k"*32, "nonce": b"n"*12}

        with open(self.test_file.name, "rb") as f:
            data = {
                "file": (f, "test_upload.txt"),
                "expire_days": "0",
                "delete_after_download": "false"
            }
            response = self.client.post("/upload", data=data, content_type="multipart/form-data")
            self.assertEqual(response.status_code, 200)
            self.assertIn("secret", response.get_data(as_text=True))

    def test_upload_missing_file_field(self):
        response = self.client.post("/upload", data={}, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)

    def test_upload_empty_files(self):
        data = {
            "file": (open(self.test_file.name, "rb"), ""),
        }
        response = self.client.post("/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)

    def test_upload_too_many_files(self):
        data = {
            "file": [(open(self.test_file.name, "rb"), "file.txt")] * (app.config["MAX_FILE_COUNT"] + 1)
        }
        response = self.client.post("/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
    
    def test_index_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    @patch("subprocess.run")
    def test_download_success(self, mock_subprocess):
        # Mock subprocess to simulate valid proof
        mock_subprocess.return_value = None

        file_id = "test123"
        ezra_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.ezra")
        ezrm_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.ezrm")

        # Simulate encrypted file
        with open(ezra_path, "wb") as f:
            f.write(b"dummy_ciphertext")

        # Simulate encrypted key + nonce (12 byte nonce + 32 byte key)
        # Step 1: Prepare key material
        nonce = b"123456789012"
        key = b"abcdefghijklmnopqrstuvwxyz123456"
        payload = nonce + key  # Do NOT pad this manually

        # Step 2: Encrypt the payload
        aesgcm = AESGCM(get_master_key())

        # Step 3: Write to .ezrm and pad just like in production
        with open(ezrm_path, "wb") as f:
            ezrm_encrypted = encrypt_ezrm(nonce + key)
            f.write(ezrm_encrypted)

        # Pad the file AFTER encryption, like the real code
        from storage import pad_file_to_exact_size
        pad_file_to_exact_size(Path(ezrm_path), 4000)


        # Send download request with valid proof
        fake_proof = {
            "proof": {
                "pi_a": ["0", "0", "1"],
                "pi_b": [["0", "0"], ["0", "0"], ["1", "0"]],
                "pi_c": ["0", "0", "1"],
                "protocol": "groth16",
                "curve": "bn128"
            },
            "public": [file_id]
        }

        response = self.client.post("/download", json=fake_proof)

        print("--> Response status:", response.status_code)
        print("--> Response data:", response.get_data(as_text=True))
        data = response.get_json()

        # Assert successful JSON response and base64 fields
        self.assertEqual(response.status_code, 200)
        self.assertIn("ciphertext", data)
        self.assertIn("nonce", data)
        self.assertIn("key", data)

    def test_download_invalid_structure(self):
        bad_data_cases = [
            {"proof": "not_a_dict", "public": ["some_id"]},
            {"proof": {}, "public": "not_a_list"},
            {"proof": {}, "public": [123]},
            {"proof": {"pi_a": [], "pi_b": [], "pi_c": []}, "public": ["some_id"]}  # missing keys
        ]
        for bad_case in bad_data_cases:
            response = self.client.post("/download", json=bad_case)
            self.assertEqual(response.status_code, 400)

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd"))
    def test_download_invalid_proof(self, mock_run):
        bad_proof = {
            "proof": {
                "pi_a": ["0", "0", "1"],
                "pi_b": [["0", "0"], ["0", "0"], ["1", "0"]],
                "pi_c": ["0", "0", "1"],
                "protocol": "groth16",
                "curve": "bn128"
            },
            "public": ["mock_id"]
        }
        response = self.client.post("/download", json=bad_proof)
        self.assertEqual(response.status_code, 403)
    
    @patch("subprocess.run")
    def test_download_malformed_ezrd(self, mock_subprocess):
        # Malformed .ezrd file (JSON decode failure)
        mock_subprocess.return_value = None
        file_id = "badjson"

        # Create required files
        with open(os.path.join(UPLOAD_FOLDER, f"{file_id}.ezra"), "wb") as f:
            f.write(b"ciphertext")
        with open(os.path.join(UPLOAD_FOLDER, f"{file_id}.ezrm"), "wb") as f:
            from encryption import encrypt_ezrm
            f.write(encrypt_ezrm(b"n" * 12 + b"k" * 32))
        with open(os.path.join(UPLOAD_FOLDER, f"{file_id}.ezrd"), "wb") as f:
            f.write(b"not a json")

        fake_proof = {
            "proof": {
                "pi_a": ["0", "0", "1"],
                "pi_b": [["0", "0"], ["0", "0"], ["1", "0"]],
                "pi_c": ["0", "0", "1"],
                "protocol": "groth16",
                "curve": "bn128"
            },
            "public": [file_id]
        }

        response = self.client.post("/download", json=fake_proof)
        self.assertEqual(response.status_code, 200)  # Still succeeds, just skips deletion

    def test_delayed_delete_mock(self):
        test_id = "dummyfile"
        # create dummy files
        for ext in ["ezra", "ezrm", "ezrd"]:
            with open(f"{UPLOAD_FOLDER}/{test_id}.{ext}", "w") as f:
                f.write("dummy")
        delayed_delete(test_id, delay=0)
        for ext in ["ezra", "ezrm", "ezrd"]:
            self.assertFalse(os.path.exists(f"{UPLOAD_FOLDER}/{test_id}.{ext}"))
    
    def test_delayed_delete_file_missing_error(self):
        # This should trigger the "except Exception as e:" block in delayed_delete
        delayed_delete("nonexistentfile", delay=0)

if __name__ == "__main__":
    unittest.main()

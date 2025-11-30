import unittest
import tempfile
import os
import json
import sys
import base64
import sqlite3
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server'))) 

from app import app
from paths import UPLOAD_DIR, DB_DIR, ensure_directories
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'server/', '.env')
load_dotenv(dotenv_path)
ensure_directories()

class FlaskRouteTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["DEBUG"] = True
        self.client = app.test_client()
        
        # Create test encrypted file
        self.test_file = tempfile.NamedTemporaryFile(delete=False)
        self.test_file.write(b"Encrypted test content")
        self.test_file.close()
        
        # Initialize test database
        os.makedirs(DB_DIR, exist_ok=True)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        schema = """
        CREATE TABLE IF NOT EXISTS expirations (
            file_id TEXT PRIMARY KEY,
            expires_at INTEGER NOT NULL,
            delete_on_download INTEGER DEFAULT 0
        );
        """
        with sqlite3.connect(DB_DIR / "expirations.db") as db:
            db.execute(schema)
            db.commit()

    def tearDown(self):
        os.unlink(self.test_file.name)
        
        # Clean up upload directory
        if os.path.exists(UPLOAD_DIR):
            for file in os.listdir(UPLOAD_DIR):
                file_path = os.path.join(UPLOAD_DIR, file)
                if os.path.basename(file_path) != ".gitkeep":
                    os.unlink(file_path)
        
        # Clean up database
        if os.path.exists(DB_DIR / "expirations.db"):
            os.unlink(DB_DIR / "expirations.db")

    def test_index_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<!DOCTYPE html>", response.data)

    def test_about_route(self):
        response = self.client.get("/about")
        self.assertEqual(response.status_code, 200)

    def test_canary_route(self):
        response = self.client.get("/canary")
        self.assertEqual(response.status_code, 200)

    def test_poseidon_endpoint(self):
        # Test valid base64 secret
        secret = b"test_secret_32_bytes_padded_here"
        secret_b64 = base64.b64encode(secret).decode()
        
        response = self.client.post("/poseidon", 
                                     json={"secret_b64": secret_b64},
                                     content_type="application/json")
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("hash", data)
        self.assertIsInstance(data["hash"], str)

    def test_poseidon_missing_input(self):
        response = self.client.post("/poseidon", 
                                     json={},
                                     content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_poseidon_invalid_base64(self):
        response = self.client.post("/poseidon", 
                                     json={"secret_b64": "not_valid_base64!!!"},
                                     content_type="application/json")
        self.assertEqual(response.status_code, 500)

    def test_upload_missing_file(self):
        response = self.client.post("/upload", data={}, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"No file provided", response.data)

    def test_upload_missing_secret(self):
        with open(self.test_file.name, "rb") as f:
            data = {
                "file": (f, "test.ezra"),
            }
            response = self.client.post("/upload", data=data, content_type="multipart/form-data")
            self.assertEqual(response.status_code, 400)
            self.assertIn(b"Missing secret", response.data)

    def test_upload_missing_proof(self):
        secret = base64.b64encode(b"test_secret_32_bytes_here_______").decode()
        
        with open(self.test_file.name, "rb") as f:
            data = {
                "file": (f, "test.ezra"),
                "secret": secret,
                "expire_hours": "24"
            }
            response = self.client.post("/upload", data=data, content_type="multipart/form-data")
            self.assertEqual(response.status_code, 400)
            self.assertIn(b"Missing ZK proof", response.data)

    def test_upload_success(self):
        secret = base64.b64encode(b"test_secret_32_bytes_here_______").decode()
        
        # Mock proof and public signals
        fake_proof = {
            "pi_a": ["1", "2", "1"],
            "pi_b": [["1", "2"], ["3", "4"], ["1", "0"]],
            "pi_c": ["5", "6", "1"],
            "protocol": "groth16",
            "curve": "bn128"
        }
        fake_public = ["123456789"]  # This becomes the file_id
        
        with open(self.test_file.name, "rb") as f:
            data = {
                "file": (f, "test.ezra"),
                "secret": secret,
                "zk_proof": json.dumps(fake_proof),
                "zk_public": json.dumps(fake_public),
                "expire_hours": "24",
                "delete_after_download": "false"
            }
            response = self.client.post("/upload", data=data, content_type="multipart/form-data")
            
            self.assertEqual(response.status_code, 200)
            result = response.get_json()
            self.assertIn("file_id", result)
            self.assertEqual(result["file_id"], "123456789")
            
            # Verify files were created
            file_id = result["file_id"]
            self.assertTrue(os.path.exists(UPLOAD_DIR / f"{file_id}.ezra"))
            self.assertTrue(os.path.exists(UPLOAD_DIR / f"{file_id}.proof.json"))
            self.assertTrue(os.path.exists(UPLOAD_DIR / f"{file_id}.public.json"))

    def test_upload_too_many_files(self):
        secret = base64.b64encode(b"test_secret_32_bytes_here_______").decode()
        fake_proof = {"pi_a": [], "pi_b": [], "pi_c": [], "protocol": "groth16", "curve": "bn128"}
        fake_public = ["123"]
        
        max_files = app.config["MAX_FILE_COUNT"]
        files = [(open(self.test_file.name, "rb"), f"file{i}.txt") for i in range(max_files + 1)]
        
        data = {
            "file": files,
            "secret": secret,
            "zk_proof": json.dumps(fake_proof),
            "zk_public": json.dumps(fake_public),
            "expire_hours": "24"
        }
        
        response = self.client.post("/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Too many files", response.data)

    @patch("subprocess.run")
    def test_download_success(self, mock_subprocess):
        # Mock successful proof verification
        mock_subprocess.return_value = None
        
        file_id = "test_file_id_123"
        
        # Create fake encrypted file
        ezra_path = UPLOAD_DIR / f"{file_id}.ezra"
        with open(ezra_path, "wb") as f:
            f.write(b"fake_encrypted_content_here")
        
        # Create expiration record
        with sqlite3.connect(DB_DIR / "expirations.db") as db:
            db.execute(
                "INSERT INTO expirations (file_id, expires_at, delete_on_download) VALUES (?, ?, ?)",
                (file_id, 9999999999, 0)
            )
        
        # Create valid proof structure
        fake_proof = {
            "pi_a": ["1", "2", "1"],
            "pi_b": [["1", "2"], ["3", "4"], ["1", "0"]],
            "pi_c": ["5", "6", "1"],
            "protocol": "groth16",
            "curve": "bn128"
        }
        fake_public = [file_id]
        
        response = self.client.post("/download", 
                                     json={"proof": fake_proof, "public": fake_public},
                                     content_type="application/json")
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("ciphertext", data)
        
        # Verify we can decode the base64
        ciphertext = base64.b64decode(data["ciphertext"])
        self.assertEqual(ciphertext, b"fake_encrypted_content_here")

    def test_download_invalid_proof_structure(self):
        bad_cases = [
            {"proof": "not_a_dict", "public": ["id"]},
            {"proof": {}, "public": "not_a_list"},
            {"proof": {}, "public": [123]},  # Not string
            {"proof": {"pi_a": []}, "public": ["id"]},  # Missing required keys
        ]
        
        for bad_case in bad_cases:
            response = self.client.post("/download", 
                                         json=bad_case,
                                         content_type="application/json")
            self.assertEqual(response.status_code, 400)

    @patch("subprocess.run", side_effect=Exception("snarkjs failed"))
    def test_download_proof_verification_error(self, mock_subprocess):
        file_id = "error_test"
        
        # Create file
        with open(UPLOAD_DIR / f"{file_id}.ezra", "wb") as f:
            f.write(b"content")
        
        fake_proof = {
            "pi_a": ["1", "2", "1"],
            "pi_b": [["1", "2"], ["3", "4"], ["1", "0"]],
            "pi_c": ["5", "6", "1"],
            "protocol": "groth16",
            "curve": "bn128"
        }
        
        response = self.client.post("/download", 
                                     json={"proof": fake_proof, "public": [file_id]},
                                     content_type="application/json")
        
        self.assertEqual(response.status_code, 500)

    @patch("subprocess.run")
    def test_download_file_not_found(self, mock_subprocess):
        mock_subprocess.return_value = None
        
        fake_proof = {
            "pi_a": ["1", "2", "1"],
            "pi_b": [["1", "2"], ["3", "4"], ["1", "0"]],
            "pi_c": ["5", "6", "1"],
            "protocol": "groth16",
            "curve": "bn128"
        }
        
        response = self.client.post("/download", 
                                     json={"proof": fake_proof, "public": ["nonexistent"]},
                                     content_type="application/json")
        
        self.assertEqual(response.status_code, 404)

    def test_413_error_handler(self):
        # This tests the custom 413 handler
        # Flask will trigger it if content is too large
        # We can't easily test this without actually sending huge data,
        # but we can at least verify the handler is registered
        self.assertIn(413, app.error_handler_spec[None])


if __name__ == "__main__":
    unittest.main()
import unittest
import os
import tempfile
from pathlib import Path
from zipfile import ZipFile
from storage import encrypt_files_to_ezra, decrypt_ezra_to_files, pad_file_to_exact_size, timestomp, pad_file_reasonably

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "test.txt"
        self.test_file.write_text("EZRA TEST FILE")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_encrypt_decrypt_ezra_to_files(self):
        # Encrypt
        result = encrypt_files_to_ezra([self.test_file])
        self.assertIn("ciphertext", result)
        self.assertIn("key", result)
        self.assertIn("nonce", result)

        # Decrypt and extract
        output_dir = Path(self.temp_dir.name) / "extracted"
        output_dir.mkdir()
        extracted_paths = decrypt_ezra_to_files(result["ciphertext"], result["key"], result["nonce"], output_dir)

        self.assertTrue(len(extracted_paths) > 0)
        extracted = extracted_paths[0]
        self.assertTrue(extracted.exists())
        self.assertEqual(extracted.read_text(), "EZRA TEST FILE")

    def test_padding_size_increases(self):
        pad_path = Path(self.temp_dir.name) / "padme.txt"
        pad_path.write_bytes(b"tiny")
        pad_file_to_exact_size(pad_path, 100)
        self.assertEqual(pad_path.stat().st_size, 100)

    def test_pad_file_reasonably_small(self):
        small_path = Path(self.temp_dir.name) / "small.txt"
        small_path.write_bytes(b"1234")
        pad_file_reasonably(small_path)
        self.assertEqual(small_path.stat().st_size, 1024 * 1024)  # 1MB

    def test_pad_file_reasonably_medium(self):
        medium_path = Path(self.temp_dir.name) / "medium.txt"
        # 1.5MB file → round up to 2MB
        medium_path.write_bytes(b"A" * int(1.5 * 1024 * 1024))
        pad_file_reasonably(medium_path)
        self.assertEqual(medium_path.stat().st_size, 2 * 1024 * 1024)

    def test_pad_file_reasonably_large(self):
        large_path = Path(self.temp_dir.name) / "large.txt"
        # 11MB → round to 15MB
        large_path.write_bytes(b"B" * (11 * 1024 * 1024))
        pad_file_reasonably(large_path)
        self.assertEqual(large_path.stat().st_size, 15 * 1024 * 1024)

    def test_timestomp_sets_epoch(self):
        timestomp([self.test_file])
        self.assertEqual(int(self.test_file.stat().st_mtime), 0)

if __name__ == "__main__":
    unittest.main()

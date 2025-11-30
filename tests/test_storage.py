import unittest
import os
import tempfile
from pathlib import Path
from zipfile import ZipFile
import io
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server'))) 
from storage import create_ezra_archive, pad_file_to_exact_size, timestomp, pad_file_reasonably

from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'server/', '.env')
load_dotenv(dotenv_path)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file1 = Path(self.temp_dir.name) / "test1.txt"
        self.test_file2 = Path(self.temp_dir.name) / "test2.txt"
        self.test_file1.write_text("EZRA TEST FILE 1")
        self.test_file2.write_text("EZRA TEST FILE 2")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_ezra_archive_single_file(self):
        """Test creating a zip archive from a single file"""
        zip_bytes = create_ezra_archive([self.test_file1])
        
        # Verify it's a valid zip
        self.assertIsInstance(zip_bytes, bytes)
        self.assertGreater(len(zip_bytes), 0)
        
        # Verify we can extract it
        with ZipFile(io.BytesIO(zip_bytes), 'r') as zipf:
            names = zipf.namelist()
            self.assertEqual(len(names), 1)
            self.assertEqual(names[0], "test1.txt")
            
            # Verify content
            content = zipf.read("test1.txt").decode('utf-8')
            self.assertEqual(content, "EZRA TEST FILE 1")

    def test_create_ezra_archive_multiple_files(self):
        """Test creating a zip archive from multiple files"""
        zip_bytes = create_ezra_archive([self.test_file1, self.test_file2])
        
        with ZipFile(io.BytesIO(zip_bytes), 'r') as zipf:
            names = zipf.namelist()
            self.assertEqual(len(names), 2)
            self.assertIn("test1.txt", names)
            self.assertIn("test2.txt", names)
            
            # Verify both contents
            self.assertEqual(zipf.read("test1.txt").decode('utf-8'), "EZRA TEST FILE 1")
            self.assertEqual(zipf.read("test2.txt").decode('utf-8'), "EZRA TEST FILE 2")

    def test_create_ezra_archive_preserves_filenames(self):
        """Test that filenames are preserved in the archive"""
        special_file = Path(self.temp_dir.name) / "special-file_123.dat"
        special_file.write_bytes(b"binary data")
        
        zip_bytes = create_ezra_archive([special_file])
        
        with ZipFile(io.BytesIO(zip_bytes), 'r') as zipf:
            names = zipf.namelist()
            self.assertIn("special-file_123.dat", names)

    def test_pad_file_to_exact_size(self):
        """Test padding a file to exact target size"""
        pad_path = Path(self.temp_dir.name) / "padme.txt"
        pad_path.write_bytes(b"tiny")
        
        original_size = pad_path.stat().st_size
        self.assertEqual(original_size, 4)
        
        pad_file_to_exact_size(pad_path, 100)
        
        self.assertEqual(pad_path.stat().st_size, 100)
        
        # Verify padding is null bytes
        content = pad_path.read_bytes()
        self.assertEqual(content[:4], b"tiny")
        self.assertEqual(content[4:], b'\x00' * 96)

    def test_pad_file_to_exact_size_no_padding_needed(self):
        """Test that padding doesn't add bytes if file is already target size or larger"""
        exact_path = Path(self.temp_dir.name) / "exact.txt"
        exact_path.write_bytes(b"X" * 100)
        
        pad_file_to_exact_size(exact_path, 100)
        self.assertEqual(exact_path.stat().st_size, 100)
        
        # Try with larger file
        larger_path = Path(self.temp_dir.name) / "larger.txt"
        larger_path.write_bytes(b"Y" * 200)
        
        pad_file_to_exact_size(larger_path, 100)
        self.assertEqual(larger_path.stat().st_size, 200)  # No change

    def test_pad_file_reasonably_small(self):
        """Test padding small files (< 1MB) to 1MB"""
        small_path = Path(self.temp_dir.name) / "small.txt"
        small_path.write_bytes(b"1234")
        
        pad_file_reasonably(small_path)
        
        self.assertEqual(small_path.stat().st_size, 1024 * 1024)  # 1MB

    def test_pad_file_reasonably_medium(self):
        """Test padding medium files (1MB-10MB) to next MB"""
        medium_path = Path(self.temp_dir.name) / "medium.txt"
        # 1.5MB file → round up to 2MB
        medium_path.write_bytes(b"A" * int(1.5 * 1024 * 1024))
        
        pad_file_reasonably(medium_path)
        
        self.assertEqual(medium_path.stat().st_size, 2 * 1024 * 1024)

    def test_pad_file_reasonably_large(self):
        """Test padding large files (10MB+) to next 5MB boundary"""
        large_path = Path(self.temp_dir.name) / "large.txt"
        # 11MB → round to 15MB
        large_path.write_bytes(b"B" * (11 * 1024 * 1024))
        
        pad_file_reasonably(large_path)
        
        self.assertEqual(large_path.stat().st_size, 15 * 1024 * 1024)

    def test_pad_file_reasonably_boundary_cases(self):
        """Test padding at exact boundaries - always rounds up"""
        # Exactly 1MB rounds up to 2MB (falls in 1MB-10MB range)
        exact_1mb = Path(self.temp_dir.name) / "exact_1mb.txt"
        exact_1mb.write_bytes(b"X" * (1024 * 1024))
        pad_file_reasonably(exact_1mb)
        self.assertEqual(exact_1mb.stat().st_size, 2 * 1024 * 1024)
        
        # Exactly 10MB rounds up to 15MB (10MB+ uses 5MB increments)
        exact_10mb = Path(self.temp_dir.name) / "exact_10mb.txt"
        exact_10mb.write_bytes(b"Y" * (10 * 1024 * 1024))
        pad_file_reasonably(exact_10mb)
        self.assertEqual(exact_10mb.stat().st_size, 15 * 1024 * 1024)

    def test_timestomp_sets_epoch(self):
        """Test that timestomping sets mtime and atime to epoch (0)"""
        timestomp([self.test_file1])
        
        self.assertEqual(int(self.test_file1.stat().st_mtime), 0)
        self.assertEqual(int(self.test_file1.stat().st_atime), 0)

    def test_timestomp_multiple_files(self):
        """Test timestomping multiple files at once"""
        timestomp([self.test_file1, self.test_file2])
        
        self.assertEqual(int(self.test_file1.stat().st_mtime), 0)
        self.assertEqual(int(self.test_file2.stat().st_mtime), 0)

    def test_timestomp_handles_missing_file(self):
        """Test that timestomp handles missing files gracefully"""
        missing = Path(self.temp_dir.name) / "doesnt_exist.txt"
        
        # Should not raise exception
        timestomp([missing])
        
        # Original file should still be timestomped
        timestomp([self.test_file1, missing])
        self.assertEqual(int(self.test_file1.stat().st_mtime), 0)


if __name__ == "__main__":
    unittest.main()
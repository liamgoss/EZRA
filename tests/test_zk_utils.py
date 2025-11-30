import unittest
from unittest.mock import patch, MagicMock
import subprocess
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server'))) 
from zk_utils import poseidon_hash

from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'server/', '.env')
load_dotenv(dotenv_path)


class ZKTests(unittest.TestCase):
    
    @patch("zk_utils.subprocess.run")
    def test_poseidon_hash_success(self, mock_run):
        """Test that poseidon_hash returns the correct hash value"""
        mock_result = MagicMock()
        mock_result.stdout = "1234567890\n"
        mock_run.return_value = mock_result

        hash_val = poseidon_hash(123456)
        
        self.assertEqual(hash_val, "1234567890")
        mock_run.assert_called_once()
        
        # Verify it called node with the right script structure
        call_args = mock_run.call_args
        self.assertEqual(call_args[0][0][0], "node")
        self.assertEqual(call_args[0][0][1], "-e")
        self.assertIn("buildPoseidon", call_args[0][0][2])
        self.assertIn("123456", call_args[0][0][2])

    @patch("zk_utils.subprocess.run")
    def test_poseidon_hash_failure(self, mock_run):
        """Test that poseidon_hash raises exception on subprocess failure"""
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd="node",
            output="",
            stderr="poseidon error"
        )
        mock_run.side_effect = error

        with self.assertRaises(subprocess.CalledProcessError):
            poseidon_hash(999)

    @patch("zk_utils.subprocess.run")
    def test_poseidon_hash_strips_whitespace(self, mock_run):
        """Test that poseidon_hash strips trailing newlines/whitespace"""
        mock_result = MagicMock()
        mock_result.stdout = "  9876543210  \n\n"
        mock_run.return_value = mock_result

        hash_val = poseidon_hash(42)
        
        self.assertEqual(hash_val, "9876543210")

    def test_poseidon_hash_integration(self):
        """Integration test - actually runs Node.js if available"""
        try:
            # This will only work if node and circomlibjs are installed
            hash_val = poseidon_hash(123)
            
            # Basic sanity checks
            self.assertIsInstance(hash_val, str)
            self.assertTrue(hash_val.isdigit())
            self.assertGreater(len(hash_val), 0)
            
            # Same input should give same output (deterministic)
            hash_val2 = poseidon_hash(123)
            self.assertEqual(hash_val, hash_val2)
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.skipTest(f"Node.js or circomlibjs not available: {e}")


if __name__ == "__main__":
    unittest.main()
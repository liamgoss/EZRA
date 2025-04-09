import unittest
from unittest.mock import patch, MagicMock, mock_open
import subprocess

from zk_utils import generate_secret, poseidon_hash, get_commitment

import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'server/', '.env')
load_dotenv(dotenv_path)

class ZKTests(unittest.TestCase):
    def test_generate_secret_returns_int(self):
        secret = generate_secret()
        self.assertIsInstance(secret, int)

    @patch("zk_utils.subprocess.run")
    def test_poseidon_hash_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = "1234567890\n"
        mock_run.return_value = mock_result

        hash_val = poseidon_hash(123456)
        self.assertEqual(hash_val, "1234567890")
        mock_run.assert_called_once()

    @patch("zk_utils.subprocess.run")
    def test_poseidon_hash_failure(self, mock_run):
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd="node",
            output="",
            stderr="poseidon error"
        )
        mock_run.side_effect = error

        with self.assertRaises(subprocess.CalledProcessError):
            poseidon_hash(999)

    @patch("zk_utils.poseidon_hash", return_value="99999")
    @patch("zk_utils.subprocess.run")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_get_commitment_runs_all_steps(self, mock_makedirs, mock_open_fn, mock_subproc, mock_poseidon):
        commitment = get_commitment(12345)

        self.assertEqual(commitment, "99999")
        mock_makedirs.assert_called_once_with("inputs", exist_ok=True)
        mock_open_fn.assert_called_with("inputs/input.json", "w")
        self.assertEqual(mock_subproc.call_count, 2)  # snarkjs wtns + prove
        mock_poseidon.assert_called_once_with(12345)


if __name__ == "__main__":
    unittest.main()

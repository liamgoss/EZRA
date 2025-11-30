import unittest, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server'))) 
from encryption import encrypt_file, decrypt_file

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'server/', '.env')
load_dotenv(dotenv_path)

class EncryptionTests(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        message = b"hello world"
        result = encrypt_file(message)
        decrypted = decrypt_file(result["ciphertext"], result["key"], result["nonce"])
        self.assertEqual(decrypted, message)

    def test_different_ciphertext_each_time(self):
        msg = b"secret"
        res1 = encrypt_file(msg)
        res2 = encrypt_file(msg)
        self.assertNotEqual(res1["ciphertext"], res2["ciphertext"])

if __name__ == "__main__":
    unittest.main()

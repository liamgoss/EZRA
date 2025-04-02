from encryption import encrypt_file, decrypt_file

def test_encryption_roundtrip():
    original_data = b"EZRA TEST FILE"
    result = encrypt_file(original_data)
    
    decrypted = decrypt_file(
        result["ciphertext"], result["key"], result["nonce"]
    )
    assert decrypted == original_data
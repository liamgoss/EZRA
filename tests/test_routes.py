import io
from app import app

def test_index_get():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200

def test_file_upload_flow(monkeypatch):
    client = app.test_client()

    dummy_file = io.BytesIO(b"this is test data")
    dummy_file.filename = "test.txt"

    # Mock encrypt_file to avoid full crypto dependency in unit test
    monkeypatch.setattr("encryption.encrypt_file", lambda x: {
        "ciphertext": b"fakecipher",
        "key": b"key",
        "nonce": b"nonce"
    })

    response = client.post("/", data={
        "file": (dummy_file, "test.txt")
    }, content_type='multipart/form-data')

    assert response.status_code == 200
    assert b"File received securely" in response.data

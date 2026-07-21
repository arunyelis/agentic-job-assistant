from backend.storage import EncryptedFileStore


def test_file_store_encrypts_bytes_at_rest(tmp_path):
    store = EncryptedFileStore(tmp_path, "unit-test-encryption-key")
    original = b"resume and application content"

    storage_key = store.put("user-123", "artifact-456", original)
    stored = (tmp_path / storage_key).read_bytes()

    assert original not in stored
    assert store.get(storage_key) == original
    assert store.delete(storage_key) is True
    assert not (tmp_path / storage_key).exists()

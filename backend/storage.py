import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"CW1"


class EncryptedFileStore:
    def __init__(self, root: Path, secret: str):
        self.root = root
        self.key = hashlib.sha256(secret.encode("utf-8")).digest()

    def put(self, user_id: str, artifact_id: str, data: bytes) -> str:
        relative = Path(user_id) / f"{artifact_id}.bin"
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        nonce = os.urandom(12)
        encrypted = AESGCM(self.key).encrypt(nonce, data, str(relative).encode("utf-8"))
        target.write_bytes(MAGIC + nonce + encrypted)
        return relative.as_posix()

    def get(self, storage_key: str) -> bytes:
        relative = Path(storage_key)
        payload = (self.root / relative).read_bytes()
        if not payload.startswith(MAGIC) or len(payload) < len(MAGIC) + 13:
            raise ValueError("The stored artifact is not valid.")
        nonce = payload[len(MAGIC) : len(MAGIC) + 12]
        encrypted = payload[len(MAGIC) + 12 :]
        return AESGCM(self.key).decrypt(
            nonce,
            encrypted,
            str(relative).encode("utf-8"),
        )

    def delete(self, storage_key: str) -> bool:
        target = self.root / Path(storage_key)
        if not target.exists():
            return False
        target.unlink()
        parent = target.parent
        if parent != self.root and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
        return True

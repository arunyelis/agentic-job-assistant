import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import User

COOKIE_NAME = "career_workspace_session"
LOCAL_ACCOUNT_EMAIL = "local-user@career-workspace.invalid"


class AuthenticationError(ValueError):
    pass


@dataclass(frozen=True)
class SessionToken:
    user_id: str
    expires_at: int


class AuthService:
    def __init__(self, secret: str, mode: str, ttl_seconds: int = 8 * 60 * 60):
        self.secret = secret.encode("utf-8")
        self.mode = mode
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(f"{value}{padding}")

    def issue(self, user_id: str) -> str:
        payload = json.dumps(
            {"user_id": user_id, "expires_at": int(time.time()) + self.ttl_seconds},
            separators=(",", ":"),
        ).encode("utf-8")
        encoded = self._encode(payload)
        signature = hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest()
        return f"{encoded}.{self._encode(signature)}"

    def verify(self, token: str | None) -> SessionToken:
        if not token or "." not in token:
            raise AuthenticationError("Authentication is required.")
        encoded, provided_signature = token.split(".", 1)
        expected = hmac.new(self.secret, encoded.encode("ascii"), hashlib.sha256).digest()
        try:
            actual = self._decode(provided_signature)
            payload = json.loads(self._decode(encoded))
        except (ValueError, json.JSONDecodeError) as error:
            raise AuthenticationError("The session is invalid.") from error
        if not hmac.compare_digest(expected, actual):
            raise AuthenticationError("The session is invalid.")
        expires_at = int(payload.get("expires_at", 0))
        if expires_at <= int(time.time()):
            raise AuthenticationError("The session has expired.")
        return SessionToken(user_id=str(payload["user_id"]), expires_at=expires_at)

    def local_user(self, session: Session) -> User:
        if self.mode != "local":
            raise AuthenticationError("Local sessions are disabled.")
        user = session.scalar(select(User).where(User.email == LOCAL_ACCOUNT_EMAIL))
        if user is None:
            user = User(email=LOCAL_ACCOUNT_EMAIL, display_name="Local workspace")
            session.add(user)
            session.commit()
        return user

    def user_from_token(
        self,
        session: Session,
        token: str | None,
        allow_deleted: bool = False,
    ) -> User:
        payload = self.verify(token)
        user = session.get(User, payload.user_id)
        if user is None:
            raise AuthenticationError("The account no longer exists.")
        if user.status != "active" and not allow_deleted:
            raise AuthenticationError("The account is not active.")
        return user

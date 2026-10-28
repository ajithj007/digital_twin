"""Password hashing and JWT helpers (no FastAPI imports, so they are easy to test)."""
import hashlib
import hmac
import os
from datetime import timedelta

import jwt

from .config import SECRET_KEY, TOKEN_EXPIRE_MINUTES
from .timeutils import utcnow

ALGORITHM = "HS256"
_ITERATIONS = 120_000


def hash_password(password: str, salt_hex: str = None) -> str:
    salt_hex = salt_hex or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), _ITERATIONS
    ).hex()
    return f"{salt_hex}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hash_password(password, salt_hex).split("$", 1)[1]
    return hmac.compare_digest(candidate, digest)


def create_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    """Returns the payload dict, or None if the token is invalid/expired."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None

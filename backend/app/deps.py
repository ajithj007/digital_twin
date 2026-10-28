"""FastAPI dependencies: current user, role checks and the device API key check."""
from typing import Optional

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import DEVICE_API_KEY
from .database import get_db, one
from .security import decode_token

bearer = HTTPBearer(auto_error=False)

ALL_ROLES = ("admin", "faculty", "student", "operations")
STAFF = ("admin", "faculty", "operations")   # may see sensor-level data
OPS = ("admin", "operations")                # may manage incidents / devices
ADMIN = ("admin",)


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    conn=Depends(get_db),
):
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expired or invalid - please log in again")
    user = one(conn.execute(
        "SELECT id, name, email, role, class_group FROM users WHERE id = ?", (int(payload["sub"]),)
    ))
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user


def require_roles(*roles):
    def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Your role does not have access to this resource")
        return user
    return checker


def verify_device_key(x_device_key: Optional[str] = Header(default=None)):
    if x_device_key != DEVICE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Device-Key header")
    return True

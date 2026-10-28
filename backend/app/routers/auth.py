from fastapi import APIRouter, Depends, HTTPException

from ..audit import log_audit
from ..database import get_db, one
from ..deps import get_current_user
from ..schemas import LoginRequest
from ..security import create_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def public_user(u):
    return {"id": u["id"], "name": u["name"], "email": u["email"], "role": u["role"], "class_group": u.get("class_group")}


@router.post("/login")
def login(body: LoginRequest, conn=Depends(get_db)):
    user = one(conn.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (body.email.strip(),)))
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    log_audit(conn, user["name"], "login", user["role"])
    conn.commit()
    return {"access_token": create_token(user["id"], user["role"]), "token_type": "bearer", "user": public_user(user)}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return public_user(user)

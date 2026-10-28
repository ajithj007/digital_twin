"""Administrator-only views: users and audit log."""
from fastapi import APIRouter, Depends

from ..database import get_db, rows
from ..deps import ADMIN, require_roles

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(user=Depends(require_roles(*ADMIN)), conn=Depends(get_db)):
    return rows(conn.execute("SELECT id, name, email, role, class_group, created_at FROM users ORDER BY id"))


@router.get("/audit")
def audit_log(limit: int = 100, user=Depends(require_roles(*ADMIN)), conn=Depends(get_db)):
    return rows(conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (max(1, min(limit, 500)),)))

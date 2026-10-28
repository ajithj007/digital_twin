"""Meta information, dashboards, analytics and global search."""
from fastapi import APIRouter, Depends, HTTPException

from .. import queries
from ..database import get_db
from ..deps import ALL_ROLES, STAFF, get_current_user, require_roles

router = APIRouter(tags=["dashboard"])


@router.get("/health")
def health(conn=Depends(get_db)):
    conn.execute("SELECT 1")
    return {"status": "ok"}


@router.get("/meta")
def meta(conn=Depends(get_db)):
    """Public: tells the UI whether data is simulated, so it can label it clearly."""
    return queries.meta(conn)


@router.get("/dashboard/summary")
def dashboard_summary(user=Depends(require_roles(*ALL_ROLES)), conn=Depends(get_db)):
    return queries.dashboard_summary(conn, role=user["role"])


@router.get("/dashboard/me")
def dashboard_me(user=Depends(get_current_user), conn=Depends(get_db)):
    return queries.dashboard_me(conn, user)


@router.get("/analytics/overview")
def analytics_overview(hours: int = 6, user=Depends(require_roles(*STAFF)), conn=Depends(get_db)):
    return queries.analytics_overview(conn, hours=max(1, min(hours, 24)))


@router.get("/search")
def search(q: str, user=Depends(get_current_user), conn=Depends(get_db)):
    if len(q.strip()) < 2:
        raise HTTPException(status_code=422, detail="Type at least 2 characters")
    return queries.search(conn, q, role=user["role"])

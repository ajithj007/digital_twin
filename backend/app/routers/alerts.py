"""Incidents / alerts: list, acknowledge, resolve."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .. import queries
from ..audit import log_audit
from ..database import get_db, one
from ..deps import ALL_ROLES, OPS, require_roles
from ..timeutils import utcnow_iso

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
def list_alerts(
    status: Optional[str] = None,       # active | acknowledged | resolved | open (= active + acknowledged)
    severity: Optional[str] = None,
    building_id: Optional[int] = None,
    limit: int = 100,
    user=Depends(require_roles(*ALL_ROLES)),
    conn=Depends(get_db),
):
    return queries.alerts_list(
        conn, status=status, severity=severity, building_id=building_id, limit=max(1, min(limit, 500)), role=user["role"]
    )


@router.get("/summary")
def alerts_summary(user=Depends(require_roles(*ALL_ROLES)), conn=Depends(get_db)):
    return queries.alert_counts(conn)


@router.get("/{alert_id}")
def get_alert(alert_id: int, user=Depends(require_roles(*ALL_ROLES)), conn=Depends(get_db)):
    found = queries.alerts_list(conn, alert_id=alert_id, role=user["role"])
    if not found:
        raise HTTPException(status_code=404, detail="Alert not found")
    return found[0]


@router.post("/{alert_id}/acknowledge")
def acknowledge(alert_id: int, user=Depends(require_roles(*OPS)), conn=Depends(get_db)):
    alert = one(conn.execute("SELECT id, status FROM alerts WHERE id = ?", (alert_id,)))
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert["status"] != "active":
        raise HTTPException(status_code=409, detail="Only active alerts can be acknowledged")
    conn.execute(
        "UPDATE alerts SET status='acknowledged', acknowledged_at=?, acknowledged_by=? WHERE id=?",
        (utcnow_iso(), user["name"], alert_id),
    )
    log_audit(conn, user["name"], "incident_acknowledged", f"alert #{alert_id}")
    conn.commit()
    return queries.alerts_list(conn, alert_id=alert_id)[0]


@router.post("/{alert_id}/resolve")
def resolve(alert_id: int, user=Depends(require_roles(*OPS)), conn=Depends(get_db)):
    alert = one(conn.execute("SELECT id, status FROM alerts WHERE id = ?", (alert_id,)))
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert["status"] == "resolved":
        raise HTTPException(status_code=409, detail="Alert is already resolved")
    conn.execute(
        "UPDATE alerts SET status='resolved', resolved_at=?, resolved_by=? WHERE id=?",
        (utcnow_iso(), user["name"], alert_id),
    )
    log_audit(conn, user["name"], "incident_resolved", f"alert #{alert_id}")
    conn.commit()
    return queries.alerts_list(conn, alert_id=alert_id)[0]

"""Configurable alert rules."""
from fastapi import APIRouter, Depends, HTTPException

from ..audit import log_audit
from ..database import get_db, one, rows
from ..deps import ADMIN, OPS, require_roles
from ..schemas import RuleCreate, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])

SEVERITIES = ("info", "warning", "critical")
OPERATORS = (">", ">=", "<", "<=")
RULE_TYPES = ("threshold", "over_capacity", "device_offline")


@router.get("")
def list_rules(user=Depends(require_roles(*OPS)), conn=Depends(get_db)):
    return rows(conn.execute("SELECT * FROM alert_rules ORDER BY id"))


@router.put("/{rule_id}")
def update_rule(rule_id: int, body: RuleUpdate, user=Depends(require_roles(*ADMIN)), conn=Depends(get_db)):
    rule = one(conn.execute("SELECT * FROM alert_rules WHERE id = ?", (rule_id,)))
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    if body.severity is not None and body.severity not in SEVERITIES:
        raise HTTPException(status_code=422, detail=f"severity must be one of {', '.join(SEVERITIES)}")
    if body.operator is not None and body.operator not in OPERATORS:
        raise HTTPException(status_code=422, detail=f"operator must be one of {', '.join(OPERATORS)}")
    new = {
        "name": body.name if body.name is not None else rule["name"],
        "operator": body.operator if body.operator is not None else rule["operator"],
        "threshold": body.threshold if body.threshold is not None else rule["threshold"],
        "severity": body.severity if body.severity is not None else rule["severity"],
        "enabled": int(body.enabled) if body.enabled is not None else rule["enabled"],
    }
    conn.execute(
        "UPDATE alert_rules SET name=?, operator=?, threshold=?, severity=?, enabled=? WHERE id=?",
        (new["name"], new["operator"], new["threshold"], new["severity"], new["enabled"], rule_id),
    )
    log_audit(conn, user["name"], "rule_updated", f"rule #{rule_id}: {new}")
    conn.commit()
    return one(conn.execute("SELECT * FROM alert_rules WHERE id = ?", (rule_id,)))


@router.post("", status_code=201)
def create_rule(body: RuleCreate, user=Depends(require_roles(*ADMIN)), conn=Depends(get_db)):
    if body.severity not in SEVERITIES or body.operator not in OPERATORS or body.rule_type not in RULE_TYPES:
        raise HTTPException(status_code=422, detail="Invalid severity, operator or rule_type")
    rule_id = conn.execute(
        "INSERT INTO alert_rules (name, alert_type, rule_type, sensor_type, operator, threshold, severity, description) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (body.name, body.alert_type, body.rule_type, body.sensor_type, body.operator, body.threshold, body.severity, body.description),
    ).lastrowid
    log_audit(conn, user["name"], "rule_created", f"rule #{rule_id} {body.name}")
    conn.commit()
    return one(conn.execute("SELECT * FROM alert_rules WHERE id = ?", (rule_id,)))

"""Rule-based alert generation (simple conditional rules - NOT machine learning / AI).

Rule types (table alert_rules):
  threshold      sensor value <operator> threshold                -> alert
  over_capacity  occupancy count > capacity * (1 + margin%/100)   -> alert (count-mode sensors only)
  device_offline no data for N seconds                            -> alert (and auto-resolved when data returns)
"""
from .audit import log_audit
from .config import ALERT_COOLDOWN_SECONDS, DEFAULT_OFFLINE_AFTER_SECONDS
from .database import rows
from .timeutils import age_seconds, parse_iso, utcnow, utcnow_iso

SEVERITY_RANK = {"info": 1, "warning": 2, "critical": 3}
OPEN_STATUSES = ("active", "acknowledged")

SENSOR_LABELS = {
    "temperature": "Temperature",
    "humidity": "Humidity",
    "occupancy": "Occupancy",
    "air_quality": "Air quality",
}


def load_rules(conn, only_enabled=True):
    sql = "SELECT * FROM alert_rules"
    if only_enabled:
        sql += " WHERE enabled = 1"
    return rows(conn.execute(sql))


def get_offline_after(conn) -> int:
    row = conn.execute(
        "SELECT threshold FROM alert_rules WHERE rule_type='device_offline' AND enabled=1 LIMIT 1"
    ).fetchone()
    return int(row["threshold"]) if row else DEFAULT_OFFLINE_AFTER_SECONDS


def compare(value: float, operator: str, threshold: float) -> bool:
    if operator == ">":
        return value > threshold
    if operator == ">=":
        return value >= threshold
    if operator == "<":
        return value < threshold
    if operator == "<=":
        return value <= threshold
    return False


def _create_or_escalate(conn, *, rule, alert_type, severity, message, ctx, value, ts, is_simulated):
    """Create an alert unless an equivalent open alert already exists.

    - open (active/acknowledged) alert with same sensor+type exists -> escalate it if severity is higher
    - alert for same sensor+type was resolved very recently -> skip (cooldown)
    Returns the alert id or None.
    """
    existing = conn.execute(
        "SELECT * FROM alerts WHERE sensor_id IS ? AND device_id IS ? AND alert_type = ? "
        "AND status IN ('active','acknowledged') ORDER BY id DESC LIMIT 1",
        (ctx.get("sensor_id"), ctx.get("device_id"), alert_type),
    ).fetchone()
    if existing:
        if SEVERITY_RANK[severity] > SEVERITY_RANK[existing["severity"]]:
            conn.execute(
                "UPDATE alerts SET severity=?, message=?, value=?, rule_id=?, status='active', "
                "acknowledged_at=NULL, acknowledged_by=NULL WHERE id=?",
                (severity, message, value, rule["id"], existing["id"]),
            )
            log_audit(conn, "system", "alert_escalated", f"alert #{existing['id']} -> {severity}")
            return existing["id"]
        return None

    last_resolved = conn.execute(
        "SELECT resolved_at FROM alerts WHERE sensor_id IS ? AND device_id IS ? AND alert_type = ? "
        "AND status='resolved' ORDER BY id DESC LIMIT 1",
        (ctx.get("sensor_id"), ctx.get("device_id"), alert_type),
    ).fetchone()
    if last_resolved and last_resolved["resolved_at"]:
        if (parse_iso(ts) - parse_iso(last_resolved["resolved_at"])).total_seconds() < ALERT_COOLDOWN_SECONDS:
            return None

    cur = conn.execute(
        "INSERT INTO alerts (rule_id, alert_type, severity, message, building_id, floor_id, room_id, "
        "sensor_id, device_id, value, status, created_at, is_simulated) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,'active',?,?)",
        (
            rule["id"], alert_type, severity, message, ctx.get("building_id"), ctx.get("floor_id"),
            ctx.get("room_id"), ctx.get("sensor_id"), ctx.get("device_id"), value, ts, int(is_simulated),
        ),
    )
    log_audit(conn, "system", "alert_generated", f"alert #{cur.lastrowid} {alert_type} ({severity}) in {ctx.get('room_name')}")
    return cur.lastrowid


def evaluate_reading(conn, ctx: dict, value: float, is_simulated: bool, ts: str, rules=None):
    """Check one new reading against the enabled rules. `ctx` describes the sensor and its location."""
    rules = rules if rules is not None else load_rules(conn)
    sensor_type = ctx["type"]
    unit = ctx.get("unit") or ""
    created = []

    # 1) threshold rules - several rules may share an alert_type; only the most severe breach fires.
    breached = [
        r for r in rules
        if r["rule_type"] == "threshold" and r["sensor_type"] == sensor_type
        and compare(value, r["operator"], r["threshold"])
    ]
    by_type = {}
    for r in breached:
        cur = by_type.get(r["alert_type"])
        if cur is None or SEVERITY_RANK[r["severity"]] > SEVERITY_RANK[cur["severity"]]:
            by_type[r["alert_type"]] = r
    for alert_type, rule in by_type.items():
        label = SENSOR_LABELS.get(sensor_type, sensor_type)
        message = (
            f"{rule['name']}: {label} {value:.1f}{unit} {rule['operator']} {rule['threshold']:g}{unit} "
            f"in {ctx.get('room_name')}"
        )
        aid = _create_or_escalate(
            conn, rule=rule, alert_type=alert_type, severity=rule["severity"], message=message,
            ctx=ctx, value=value, ts=ts, is_simulated=is_simulated,
        )
        if aid:
            created.append(aid)

    # 2) over-capacity rule (count-mode occupancy sensors only - presence sensors cannot be compared)
    if sensor_type == "occupancy" and ctx.get("sensing_mode") == "count":
        for rule in rules:
            if rule["rule_type"] != "over_capacity":
                continue
            limit = ctx["capacity"] * (1 + rule["threshold"] / 100.0)
            if value > limit:
                message = (
                    f"{rule['name']}: estimated occupancy {int(round(value))} exceeds capacity "
                    f"{ctx['capacity']} in {ctx.get('room_name')}"
                )
                aid = _create_or_escalate(
                    conn, rule=rule, alert_type=rule["alert_type"], severity=rule["severity"],
                    message=message, ctx=ctx, value=value, ts=ts, is_simulated=is_simulated,
                )
                if aid:
                    created.append(aid)
    return created


def resolve_device_offline_alerts(conn, device_id: int, ts: str) -> int:
    cur = conn.execute(
        "UPDATE alerts SET status='resolved', resolved_at=?, resolved_by='system' "
        "WHERE device_id=? AND alert_type='device_offline' AND status IN ('active','acknowledged')",
        (ts, device_id),
    )
    if cur.rowcount:
        log_audit(conn, "system", "device_online", f"device #{device_id} is sending data again")
    return cur.rowcount


def check_devices(conn):
    """Mark devices without recent data as offline by creating a device_offline alert."""
    rule = conn.execute(
        "SELECT * FROM alert_rules WHERE rule_type='device_offline' AND enabled=1 LIMIT 1"
    ).fetchone()
    if not rule:
        return []
    rule = dict(rule)
    now = utcnow()
    ts = utcnow_iso()
    created = []
    devices = rows(conn.execute(
        "SELECT d.*, r.name AS room_name, r.floor_id FROM devices d JOIN rooms r ON r.id = d.room_id"
    ))
    for d in devices:
        age = age_seconds(d["last_seen"], now)
        if age is not None and age <= rule["threshold"]:
            continue
        ctx = {
            "sensor_id": None, "device_id": d["id"], "room_id": d["room_id"], "room_name": d["room_name"],
            "building_id": d["building_id"], "floor_id": d["floor_id"],
        }
        since = "has never reported data" if age is None else f"sent no data for {int(age)} s"
        message = f"{rule['name']}: device {d['device_uid']} {since} ({d['room_name']})"
        aid = _create_or_escalate(
            conn, rule=rule, alert_type="device_offline", severity=rule["severity"], message=message,
            ctx=ctx, value=None, ts=ts, is_simulated=bool(d["is_simulated"]),
        )
        if aid:
            created.append(aid)
    return created

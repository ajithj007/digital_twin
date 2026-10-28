"""Storing readings (from the simulator or from real ESP32 devices) and triggering the alert rules."""
import math

from . import alert_engine
from .database import rows
from .timeutils import utcnow_iso

# Plausible physical ranges used to reject garbage values coming from hardware.
VALID_RANGES = {
    "temperature": (-40.0, 85.0),
    "humidity": (0.0, 100.0),
    "occupancy": (0.0, 10000.0),
    "air_quality": (0.0, 10000.0),
}

SENSOR_CONTEXT_SQL = """
SELECT s.id AS sensor_id, s.device_id, s.room_id, s.type, s.unit, s.sensing_mode, s.last_value,
       d.device_uid, d.is_simulated AS device_simulated,
       r.name AS room_name, r.room_type, r.capacity, r.building_id, r.floor_id
FROM sensors s
JOIN devices d ON d.id = s.device_id
JOIN rooms r ON r.id = s.room_id
"""


def load_sensor_contexts(conn, device_id=None):
    sql = SENSOR_CONTEXT_SQL
    params = ()
    if device_id is not None:
        sql += " WHERE s.device_id = ?"
        params = (device_id,)
    return rows(conn.execute(sql, params))


def record_reading(conn, ctx: dict, value: float, *, is_simulated: bool, ts: str = None, rules=None):
    ts = ts or utcnow_iso()
    conn.execute(
        "INSERT INTO readings (sensor_id, value, recorded_at, is_simulated) VALUES (?,?,?,?)",
        (ctx["sensor_id"], value, ts, int(is_simulated)),
    )
    conn.execute(
        "UPDATE sensors SET last_value=?, last_recorded_at=?, last_is_simulated=? WHERE id=?",
        (value, ts, int(is_simulated), ctx["sensor_id"]),
    )
    return alert_engine.evaluate_reading(conn, ctx, value, is_simulated, ts, rules=rules)


def touch_device(conn, device_id: int, ts: str = None):
    ts = ts or utcnow_iso()
    conn.execute("UPDATE devices SET last_seen=? WHERE id=?", (ts, device_id))
    alert_engine.resolve_device_offline_alerts(conn, device_id, ts)


def validate_value(sensor_type: str, value) -> str:
    """Return an error message, or '' if the value is acceptable."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "value must be a number"
    if math.isnan(value) or math.isinf(value):
        return "value must be a finite number"
    low, high = VALID_RANGES.get(sensor_type, (-math.inf, math.inf))
    if not (low <= value <= high):
        return f"value {value} outside plausible range {low}..{high} for {sensor_type}"
    return ""


def ingest_payload(conn, device: dict, readings: list):
    """Store readings posted by a real device.

    `readings` is a list of {"sensor_type": str, "value": number}.
    Returns (accepted_count, rejected_list). The server receive time is used as the timestamp.
    """
    ts = utcnow_iso()
    rules = alert_engine.load_rules(conn)
    contexts = {c["type"]: c for c in load_sensor_contexts(conn, device["id"])}
    accepted, rejected = 0, []
    for item in readings:
        stype, value = item.get("sensor_type"), item.get("value")
        ctx = contexts.get(stype)
        if ctx is None:
            rejected.append({"sensor_type": stype, "reason": "device has no sensor of this type"})
            continue
        error = validate_value(stype, value)
        if error:
            rejected.append({"sensor_type": stype, "reason": error})
            continue
        record_reading(conn, ctx, float(value), is_simulated=False, ts=ts, rules=rules)
        accepted += 1
    if accepted:
        touch_device(conn, device["id"], ts)
    return accepted, rejected

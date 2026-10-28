"""Read-side business logic: builds the JSON-friendly structures returned by the API routers."""
from collections import defaultdict
from datetime import timedelta

from . import timetable as tt
from .alert_engine import get_offline_after
from .campus_data import PERIODS
from .config import SIMULATOR_ENABLED
from .database import one, rows
from .status import compute_location_statuses, device_is_online, worst_status
from .timeutils import now_ist, to_iso, utcnow

SCHEDULABLE_TYPES = ("classroom", "lab", "seminar")


# --------------------------------------------------------------------------- helpers
def latest_by_room(conn):
    out = defaultdict(dict)
    for s in conn.execute(
        "SELECT id, room_id, type, unit, sensing_mode, last_value, last_recorded_at, last_is_simulated FROM sensors"
    ):
        out[s["room_id"]][s["type"]] = dict(s)
    return out


def device_states(conn):
    """{device_id: online?} plus {room_id: [online flags]} using the configurable offline rule."""
    offline_after = get_offline_after(conn)
    now = utcnow()
    by_id, by_room = {}, defaultdict(list)
    for d in conn.execute("SELECT id, room_id, last_seen FROM devices"):
        online = device_is_online(d["last_seen"], offline_after, now)
        by_id[d["id"]] = online
        by_room[d["room_id"]].append(online)
    return by_id, by_room


def _class_summary(c):
    if not c:
        return None
    return {
        "course": c["course"], "faculty": c["faculty"], "class_group": c["class_group"],
        "start_time": c["start_time"], "end_time": c["end_time"],
    }


def _num(value, digits=1):
    return None if value is None else round(value, digits)


# --------------------------------------------------------------------------- meta
def meta(conn):
    sim = conn.execute("SELECT COUNT(*) c FROM devices WHERE is_simulated=1").fetchone()["c"]
    real = conn.execute("SELECT COUNT(*) c FROM devices WHERE is_simulated=0").fetchone()["c"]
    if real == 0:
        source = "simulated"
    elif sim == 0:
        source = "hardware"
    else:
        source = "mixed"
    return {
        "project": "ASIET Campus Digital Twin",
        "data_source": source,
        "simulated_devices": sim,
        "hardware_devices": real,
        "simulator_enabled": SIMULATOR_ENABLED,
        "campus_data_is_sample": True,
        "timetable_is_sample": True,
        "server_time": to_iso(utcnow()),
    }


# --------------------------------------------------------------------------- rooms
def rooms_overview(conn, building_id=None, floor_id=None, room_type=None, room_id=None):
    sql = (
        "SELECT r.id, r.code, r.name, r.room_type, r.capacity, r.monitored, r.building_id, r.floor_id, "
        "b.name AS building_name, b.code AS building_code, f.name AS floor_name, f.level AS floor_level "
        "FROM rooms r JOIN buildings b ON b.id = r.building_id JOIN floors f ON f.id = r.floor_id WHERE 1=1"
    )
    params = []
    if building_id is not None:
        sql += " AND r.building_id = ?"
        params.append(building_id)
    if floor_id is not None:
        sql += " AND r.floor_id = ?"
        params.append(floor_id)
    if room_type:
        sql += " AND r.room_type = ?"
        params.append(room_type)
    if room_id is not None:
        sql += " AND r.id = ?"
        params.append(room_id)
    sql += " ORDER BY b.id, f.level, r.id"
    result = rows(conn.execute(sql, params))

    statuses = compute_location_statuses(conn)["rooms"]
    latest = latest_by_room(conn)
    classes = tt.active_classes(conn)
    dev_by_id, dev_by_room = device_states(conn)

    for r in result:
        vals = latest.get(r["id"], {})
        occ = vals.get("occupancy")
        r["status"] = statuses.get(r["id"], "no_data")
        r["has_sensors"] = bool(vals)
        r["devices_total"] = len(dev_by_room.get(r["id"], []))
        r["devices_online"] = sum(1 for o in dev_by_room.get(r["id"], []) if o)
        r["occupancy"] = None if not occ or occ["last_value"] is None else int(round(occ["last_value"]))
        r["occupancy_mode"] = occ["sensing_mode"] if occ else None
        r["occupancy_pct"] = (
            round(100.0 * r["occupancy"] / r["capacity"]) if occ and occ["sensing_mode"] == "count" and r["occupancy"] is not None and r["capacity"] else None
        )
        for key in ("temperature", "humidity", "air_quality"):
            r[key] = _num(vals.get(key, {}).get("last_value"))
        stamps = [v["last_recorded_at"] for v in vals.values() if v["last_recorded_at"]]
        r["last_update"] = max(stamps) if stamps else None
        r["data_simulated"] = any(v["last_is_simulated"] for v in vals.values()) if vals else False
        cls = classes.get(r["id"])
        r["in_class"] = cls is not None
        r["current_class"] = _class_summary(cls)
    return result


def room_detail(conn, room_id):
    found = rooms_overview(conn, room_id=room_id)
    if not found:
        return None
    room = found[0]
    room["sensors"] = rows(conn.execute(
        "SELECT s.id, s.type, s.unit, s.sensing_mode, s.last_value, s.last_recorded_at, s.last_is_simulated, "
        "d.id AS device_id, d.device_uid, d.last_seen FROM sensors s JOIN devices d ON d.id = s.device_id "
        "WHERE s.room_id = ? ORDER BY s.type", (room_id,)
    ))
    dev_by_id, _ = device_states(conn)
    for s in room["sensors"]:
        s["device_online"] = dev_by_id.get(s["device_id"], False)
    nxt = tt.next_class(conn, room_id)
    room["next_class"] = _class_summary(nxt)
    if nxt:
        room["next_class"]["day_name"] = nxt["day_name"]
        room["next_class"]["day_offset"] = nxt["day_offset"]
    room["alerts"] = alerts_list(conn, room_id=room_id, status="open", limit=20)
    return room


# --------------------------------------------------------------------------- buildings
def _aggregate_rooms(room_list):
    count_rooms = [r for r in room_list if r["occupancy_mode"] == "count" and r["occupancy"] is not None]
    occ = sum(r["occupancy"] for r in count_rooms)
    cap = sum(r["capacity"] for r in count_rooms)
    return {
        "occupancy": occ,
        "occupancy_capacity": cap,
        "occupancy_pct": round(100.0 * occ / cap) if cap else None,
        "rooms_count": len(room_list),
        "monitored_rooms": sum(1 for r in room_list if r["has_sensors"]),
    }


def buildings_overview(conn, rooms=None):
    rooms = rooms if rooms is not None else rooms_overview(conn)
    statuses = compute_location_statuses(conn)["buildings"]
    dev_by_id, _ = device_states(conn)
    dev_counts = defaultdict(lambda: [0, 0])
    for d in conn.execute("SELECT id, building_id FROM devices"):
        dev_counts[d["building_id"]][0] += 1
        dev_counts[d["building_id"]][1] += 1 if dev_by_id.get(d["id"]) else 0
    alert_counts = defaultdict(lambda: {"active": 0, "open": 0})
    for a in conn.execute("SELECT building_id, status FROM alerts WHERE status IN ('active','acknowledged')"):
        alert_counts[a["building_id"]]["open"] += 1
        if a["status"] == "active":
            alert_counts[a["building_id"]]["active"] += 1

    by_building = defaultdict(list)
    for r in rooms:
        by_building[r["building_id"]].append(r)

    out = []
    for b in rows(conn.execute("SELECT * FROM buildings ORDER BY id")):
        b.update(_aggregate_rooms(by_building[b["id"]]))
        b["status"] = statuses.get(b["id"], "no_data")
        b["devices_total"], b["devices_online"] = dev_counts[b["id"]]
        b["active_alerts"] = alert_counts[b["id"]]["active"]
        b["open_alerts"] = alert_counts[b["id"]]["open"]
        out.append(b)
    return out


def building_detail(conn, building_id):
    building = one(conn.execute("SELECT * FROM buildings WHERE id = ?", (building_id,)))
    if not building:
        return None
    all_rooms = rooms_overview(conn, building_id=building_id)
    overview = next(b for b in buildings_overview(conn) if b["id"] == building_id)
    building.update({k: overview[k] for k in (
        "status", "occupancy", "occupancy_capacity", "occupancy_pct", "rooms_count", "monitored_rooms",
        "devices_total", "devices_online", "active_alerts", "open_alerts")})
    floors = rows(conn.execute("SELECT * FROM floors WHERE building_id = ? ORDER BY level", (building_id,)))
    for f in floors:
        f_rooms = [r for r in all_rooms if r["floor_id"] == f["id"]]
        f.update(_aggregate_rooms(f_rooms))
        f["status"] = worst_status({r["status"] for r in f_rooms}) if f_rooms else "no_data"
        f["rooms"] = f_rooms
    building["floors"] = floors
    return building


# --------------------------------------------------------------------------- sensors & devices
def sensors_list(conn, building_id=None, floor_id=None, room_id=None, sensor_type=None):
    sql = (
        "SELECT s.id, s.type, s.unit, s.sensing_mode, s.last_value, s.last_recorded_at, s.last_is_simulated, "
        "s.device_id, d.device_uid, d.last_seen, r.id AS room_id, r.name AS room_name, r.capacity, "
        "b.id AS building_id, b.name AS building_name, f.id AS floor_id, f.name AS floor_name "
        "FROM sensors s JOIN devices d ON d.id = s.device_id JOIN rooms r ON r.id = s.room_id "
        "JOIN buildings b ON b.id = r.building_id JOIN floors f ON f.id = r.floor_id WHERE 1=1"
    )
    params = []
    for column, value in (("b.id", building_id), ("f.id", floor_id), ("r.id", room_id), ("s.type", sensor_type)):
        if value is not None:
            sql += f" AND {column} = ?"
            params.append(value)
    sql += " ORDER BY b.id, f.level, r.id, s.type"
    result = rows(conn.execute(sql, params))
    dev_by_id, _ = device_states(conn)
    for s in result:
        s["device_online"] = dev_by_id.get(s["device_id"], False)
    return result


def devices_list(conn, building_id=None, status=None):
    sql = (
        "SELECT d.*, r.name AS room_name, b.name AS building_name, f.name AS floor_name "
        "FROM devices d JOIN rooms r ON r.id = d.room_id JOIN buildings b ON b.id = d.building_id "
        "JOIN floors f ON f.id = r.floor_id WHERE 1=1"
    )
    params = []
    if building_id is not None:
        sql += " AND d.building_id = ?"
        params.append(building_id)
    sql += " ORDER BY b.id, r.id"
    devices = rows(conn.execute(sql, params))
    dev_by_id, _ = device_states(conn)
    sensors = defaultdict(list)
    for s in conn.execute("SELECT device_id, type, unit, last_value, last_recorded_at FROM sensors ORDER BY type"):
        sensors[s["device_id"]].append(dict(s))
    out = []
    for d in devices:
        d["status"] = "online" if dev_by_id.get(d["id"]) else "offline"
        d["sensors"] = sensors[d["id"]]
        d["source"] = "simulated" if d["is_simulated"] else "hardware"
        if status and d["status"] != status:
            continue
        out.append(d)
    return out


def device_detail(conn, device_id):
    found = [d for d in devices_list(conn) if d["id"] == device_id]
    if not found:
        return None
    d = found[0]
    d["readings_received"] = conn.execute(
        "SELECT COUNT(*) c FROM readings r JOIN sensors s ON s.id = r.sensor_id WHERE s.device_id = ?", (device_id,)
    ).fetchone()["c"]
    d["recent_alerts"] = alerts_list(conn, device_id=device_id, limit=10)
    return d


# --------------------------------------------------------------------------- alerts
ALERT_SQL = (
    "SELECT a.*, b.name AS building_name, f.name AS floor_name, f.level AS floor_level, r.name AS room_name, "
    "d.device_uid, s.type AS sensor_type, s.unit AS sensor_unit "
    "FROM alerts a LEFT JOIN buildings b ON b.id = a.building_id LEFT JOIN floors f ON f.id = a.floor_id "
    "LEFT JOIN rooms r ON r.id = a.room_id LEFT JOIN devices d ON d.id = a.device_id "
    "LEFT JOIN sensors s ON s.id = a.sensor_id WHERE 1=1"
)


def alerts_list(conn, status=None, severity=None, building_id=None, room_id=None, device_id=None,
                alert_id=None, limit=100, role=None):
    sql = ALERT_SQL
    params = []
    if alert_id is not None:
        sql += " AND a.id = ?"
        params.append(alert_id)
    if status == "open":
        sql += " AND a.status IN ('active','acknowledged')"
    elif status:
        sql += " AND a.status = ?"
        params.append(status)
    if severity:
        sql += " AND a.severity = ?"
        params.append(severity)
    if building_id is not None:
        sql += " AND a.building_id = ?"
        params.append(building_id)
    if room_id is not None:
        sql += " AND a.room_id = ?"
        params.append(room_id)
    if device_id is not None:
        sql += " AND a.device_id = ?"
        params.append(device_id)
    if role == "student":  # students only see active emergency-type alerts, without device details
        sql += " AND a.status = 'active' AND a.severity IN ('warning','critical') AND a.alert_type != 'device_offline'"
    sql += " ORDER BY CASE a.status WHEN 'active' THEN 0 WHEN 'acknowledged' THEN 1 ELSE 2 END, a.id DESC LIMIT ?"
    params.append(limit)
    result = rows(conn.execute(sql, params))
    if role == "student":
        for a in result:
            for key in ("device_uid", "device_id", "sensor_id", "sensor_type", "sensor_unit", "value", "rule_id"):
                a[key] = None
    return result


def alert_counts(conn):
    counts = {"active": 0, "acknowledged": 0, "resolved": 0, "critical": 0, "warning": 0, "info": 0}
    for r in conn.execute("SELECT status, severity, COUNT(*) c FROM alerts GROUP BY status, severity"):
        counts[r["status"]] += r["c"]
        if r["status"] == "active":
            counts[r["severity"]] += r["c"]
    return counts


# --------------------------------------------------------------------------- time series
def thresholds_for(conn, sensor_type):
    return rows(conn.execute(
        "SELECT name, severity, operator, threshold AS value FROM alert_rules "
        "WHERE enabled=1 AND rule_type='threshold' AND sensor_type=? ORDER BY threshold", (sensor_type,)
    ))


def build_series(conn, *, sensor_type, minutes=60, building_id=None, floor_id=None, room_id=None,
                 group_by_building=False):
    """Per-sensor average per time bucket, then avg/min/max/sum across sensors.

    (Averaging per sensor first makes the 'sum' correct for occupancy: sum of room occupancies.)
    """
    minutes = max(5, min(int(minutes), 24 * 60))
    bucket = max(60, minutes)  # seconds -> roughly 60 points per chart
    since = to_iso(utcnow() - timedelta(minutes=minutes))
    where = ["s.type = ?", "rd.recorded_at >= ?"]
    params = [sensor_type, since]
    for column, value in (("rm.building_id", building_id), ("rm.floor_id", floor_id), ("rm.id", room_id)):
        if value is not None:
            where.append(f"{column} = ?")
            params.append(value)
    inner = (
        f"SELECT rd.sensor_id AS sid, rm.building_id AS bid, "
        f"CAST(strftime('%s', rd.recorded_at) AS INTEGER) / {bucket} * {bucket} AS bkt, AVG(rd.value) AS v "
        f"FROM readings rd JOIN sensors s ON s.id = rd.sensor_id JOIN rooms rm ON rm.id = s.room_id "
        f"WHERE {' AND '.join(where)} GROUP BY rd.sensor_id, bkt"
    )
    group_cols = "bkt, bid" if group_by_building else "bkt"
    select_cols = "bkt, bid" if group_by_building else "bkt, NULL AS bid"
    outer = (
        f"SELECT {select_cols}, AVG(v) AS avg, MIN(v) AS min, MAX(v) AS max, SUM(v) AS sum, COUNT(*) AS sensors "
        f"FROM ({inner}) GROUP BY {group_cols} ORDER BY bkt"
    )

    def point(r):
        from datetime import datetime, timezone
        return {
            "t": to_iso(datetime.fromtimestamp(r["bkt"], tz=timezone.utc)),
            "avg": _num(r["avg"], 2), "min": _num(r["min"], 2), "max": _num(r["max"], 2),
            "sum": _num(r["sum"], 1), "sensors": r["sensors"],
        }

    result = conn.execute(outer, params).fetchall()
    if group_by_building:
        grouped = defaultdict(list)
        for r in result:
            grouped[r["bid"]].append(point(r))
        return grouped
    return [point(r) for r in result]


# --------------------------------------------------------------------------- dashboards
def dashboard_summary(conn, role="admin"):
    rooms = rooms_overview(conn)
    buildings = buildings_overview(conn, rooms)
    agg = _aggregate_rooms(rooms)
    counts = alert_counts(conn)
    dev_by_id, _ = device_states(conn)
    devices_total = len(dev_by_id)
    devices_online = sum(1 for o in dev_by_id.values() if o)

    schedulable = [r for r in rooms if r["room_type"] in SCHEDULABLE_TYPES]
    in_class = [r for r in schedulable if r["in_class"]]
    temps = [r["temperature"] for r in rooms if r["temperature"] is not None]
    hums = [r["humidity"] for r in rooms if r["humidity"] is not None]
    stamps = [r["last_update"] for r in rooms if r["last_update"]]

    critical_locations = [
        {"room_id": r["id"], "room_name": r["name"], "building_id": r["building_id"],
         "building_name": r["building_name"], "floor_id": r["floor_id"], "status": r["status"]}
        for r in rooms if r["status"] in ("critical", "warning")
    ]
    summary = {
        "campus_occupancy": agg["occupancy"],
        "campus_capacity": agg["occupancy_capacity"],
        "campus_occupancy_pct": agg["occupancy_pct"],
        "occupancy_note": "Estimated people count from count-mode occupancy sensors (SIMULATED unless real hardware is connected).",
        "buildings_count": len(buildings),
        "rooms_count": len(rooms),
        "monitored_rooms": agg["monitored_rooms"],
        "alerts": counts,
        "active_incidents": counts["active"],
        "acknowledged_incidents": counts["acknowledged"],
        "devices_total": devices_total,
        "devices_online": devices_online,
        "devices_offline": devices_total - devices_online,
        "sensor_health_pct": round(100.0 * devices_online / devices_total) if devices_total else None,
        "schedulable_rooms": len(schedulable),
        "rooms_in_class_now": len(in_class),
        "room_utilization_pct": round(100.0 * len(in_class) / len(schedulable)) if schedulable else None,
        "avg_temperature": _num(sum(temps) / len(temps)) if temps else None,
        "avg_humidity": _num(sum(hums) / len(hums)) if hums else None,
        "last_data_received": max(stamps) if stamps else None,
        "campus_status": worst_status({b["status"] for b in buildings}),
        "buildings": buildings,
        "critical_locations": critical_locations,
        "recent_alerts": alerts_list(conn, limit=6, role=role),
    }
    if role == "student":  # students do not need device / sensor-health details
        for key in ("devices_total", "devices_online", "devices_offline", "sensor_health_pct", "avg_temperature",
                    "avg_humidity", "monitored_rooms"):
            summary[key] = None
    return summary


def free_rooms_next_hour(conn, limit=6):
    now = now_ist()
    start = now.strftime("%H:%M")
    end_dt = now + timedelta(hours=1)
    end = end_dt.strftime("%H:%M") if end_dt.date() == now.date() else "23:59"
    available, _ = tt.availability(conn, now, start, end)
    available = [r for r in available if r["room_type"] in SCHEDULABLE_TYPES]
    return available[:limit]


def dashboard_me(conn, user):
    now = now_ist()
    out = {
        "today": now.strftime("%A, %d %B %Y"),
        "time_ist": now.strftime("%H:%M"),
        "day_of_week": now.weekday(),
        "announcements": rows(conn.execute("SELECT * FROM announcements ORDER BY id")),
        "free_rooms_next_hour": free_rooms_next_hour(conn),
        "timetable_is_sample": True,
    }
    if user["role"] == "faculty":
        mine_today = tt.classes_on_day(conn, now.weekday(), faculty=user["name"])
        weekly = tt.weekly_timetable(conn, faculty=user["name"])
        out["todays_classes"] = mine_today
        room_ids = sorted({c["room_id"] for c in weekly})
        statuses = compute_location_statuses(conn)["rooms"]
        out["assigned_rooms"] = [
            {"room_id": r["id"], "room_name": r["name"], "building_id": r["building_id"], "building_name": r["building_name"],
             "floor_id": r["floor_id"], "status": r["status"], "in_class": r["in_class"]}
            for r in rooms_overview(conn) if r["id"] in room_ids
        ]
        out["weekly_class_count"] = len(weekly)
    if user["role"] == "student":
        out["class_group"] = user.get("class_group")
        out["todays_classes"] = tt.classes_on_day(conn, now.weekday(), class_group=user.get("class_group"))
    return out


# --------------------------------------------------------------------------- analytics
def analytics_overview(conn, hours=6):
    minutes = int(hours * 60)
    buildings = buildings_overview(conn)
    names = {b["id"]: b["name"] for b in buildings}

    def grouped(sensor_type):
        data = build_series(conn, sensor_type=sensor_type, minutes=minutes, group_by_building=True)
        return [{"building_id": bid, "building_name": names.get(bid, str(bid)), "points": pts} for bid, pts in data.items()]

    by_sev = rows(conn.execute("SELECT severity AS label, COUNT(*) AS value FROM alerts GROUP BY severity"))
    by_type = rows(conn.execute("SELECT alert_type AS label, COUNT(*) AS value FROM alerts GROUP BY alert_type ORDER BY value DESC"))
    by_status = rows(conn.execute("SELECT status AS label, COUNT(*) AS value FROM alerts GROUP BY status"))

    sched_hours = tt.weekly_scheduled_hours(conn)
    available_hours = sum(
        (int(e[:2]) * 60 + int(e[3:]) - int(s[:2]) * 60 - int(s[3:])) / 60.0 for s, e in PERIODS
    ) * 6
    room_util = []
    for r in rooms_overview(conn):
        if r["room_type"] in SCHEDULABLE_TYPES:
            h = sched_hours.get(r["id"], 0.0)
            room_util.append({
                "room_id": r["id"], "room_name": r["name"], "building_name": r["building_name"],
                "scheduled_hours": round(h, 1), "utilization_pct": round(100.0 * h / available_hours) if available_hours else 0,
            })
    room_util.sort(key=lambda x: -x["utilization_pct"])

    return {
        "hours": hours,
        "occupancy_trend": build_series(conn, sensor_type="occupancy", minutes=minutes),
        "temperature_by_building": grouped("temperature"),
        "humidity_by_building": grouped("humidity"),
        "alerts_by_severity": by_sev,
        "alerts_by_type": by_type,
        "alerts_by_status": by_status,
        "building_utilization": [
            {"building_name": b["name"], "occupancy_pct": b["occupancy_pct"], "occupancy": b["occupancy"],
             "capacity": b["occupancy_capacity"]} for b in buildings
        ],
        "room_utilization": room_util,
        "room_utilization_note": "Scheduled hours from the SAMPLE timetable (Mon-Sat, teaching periods only).",
        "sensor_availability": [
            {"building_name": b["name"], "devices_total": b["devices_total"], "devices_online": b["devices_online"],
             "availability_pct": round(100.0 * b["devices_online"] / b["devices_total"]) if b["devices_total"] else None}
            for b in buildings
        ],
    }


# --------------------------------------------------------------------------- search
def search(conn, q, role="admin", limit=6):
    like = f"%{q.strip()}%"
    results = []
    for b in conn.execute("SELECT id, name, code FROM buildings WHERE name LIKE ? OR code LIKE ? LIMIT ?", (like, like, limit)):
        results.append({"type": "building", "id": b["id"], "label": b["name"], "sublabel": "Building", "building_id": b["id"]})
    for r in conn.execute(
        "SELECT r.id, r.name, r.code, r.building_id, r.floor_id, b.name AS bname, f.name AS fname FROM rooms r "
        "JOIN buildings b ON b.id = r.building_id JOIN floors f ON f.id = r.floor_id "
        "WHERE r.name LIKE ? OR r.code LIKE ? LIMIT ?", (like, like, limit)
    ):
        results.append({"type": "room", "id": r["id"], "label": r["name"], "sublabel": f"{r['bname']} - {r['fname']}",
                        "building_id": r["building_id"], "floor_id": r["floor_id"], "room_id": r["id"]})
    if role in ("admin", "operations"):
        for d in conn.execute(
            "SELECT d.id, d.device_uid, d.name, r.name AS rname FROM devices d JOIN rooms r ON r.id = d.room_id "
            "WHERE d.device_uid LIKE ? OR d.name LIKE ? LIMIT ?", (like, like, limit)
        ):
            results.append({"type": "device", "id": d["id"], "label": d["device_uid"], "sublabel": f"Device - {d['rname']}"})
    if role != "student":
        for a in conn.execute("SELECT id, message, status FROM alerts WHERE message LIKE ? ORDER BY id DESC LIMIT ?", (like, limit)):
            results.append({"type": "alert", "id": a["id"], "label": a["message"][:70], "sublabel": f"Incident #{a['id']} - {a['status']}"})
    return results

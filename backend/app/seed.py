"""Creates the SAMPLE database content on first start.

Run manually with:   python -m app.seed --reset      (deletes the old database file first)
"""
import random
import sys
from contextlib import closing
from datetime import timedelta
from pathlib import Path

from . import campus_data as cd
from . import simulator
from .config import DB_PATH, SIMULATOR_BACKFILL_HOURS
from .database import get_conn, init_db
from .security import hash_password
from .timeutils import to_iso, utcnow, utcnow_iso

SENSOR_DEFS = {
    "temperature": ("°C", "value"),
    "humidity": ("%", "value"),
    "occupancy": ("people", "count"),   # SIMULATED people count; real PIR sensors only give presence
    "air_quality": ("ppm", "value"),    # CO2-equivalent
}


def seed_if_empty(conn) -> bool:
    if conn.execute("SELECT COUNT(*) c FROM buildings").fetchone()["c"] > 0:
        return False
    seed_all(conn)
    return True


def seed_all(conn):
    now = utcnow_iso()
    _seed_users(conn, now)
    room_ids = _seed_campus(conn, now)
    _seed_rules(conn)
    _seed_timetable(conn, room_ids)
    for title, body in cd.ANNOUNCEMENTS:
        conn.execute("INSERT INTO announcements (title, body, created_at) VALUES (?,?,?)", (title, body, now))
    conn.commit()

    # simulated history for the charts (clearly flagged as simulated in the database)
    lab = conn.execute("SELECT id FROM rooms WHERE code = '204'").fetchone()
    spike = (lab["id"], 150, 20, 35.5) if lab else None
    simulator.backfill(conn, hours=SIMULATOR_BACKFILL_HOURS, spike=spike)
    _seed_sample_alerts(conn, lab["id"] if lab else None)
    conn.commit()


def _seed_users(conn, now):
    for name, email, password, role, group in cd.DEMO_USERS:
        conn.execute(
            "INSERT INTO users (name, email, password_hash, role, class_group, created_at) VALUES (?,?,?,?,?,?)",
            (name, email, hash_password(password), role, group, now),
        )


def _seed_campus(conn, now):
    room_ids = {}
    for b in cd.BUILDINGS:
        floors = b["floors"]
        height = b.get("height", cd.FLOOR_HEIGHT * len(floors))
        cur = conn.execute(
            "INSERT INTO buildings (code, name, description, x, z, width, depth, height, floors_count) VALUES (?,?,?,?,?,?,?,?,?)",
            (b["code"], b["name"], b["description"], b["x"], b["z"], b["width"], b["depth"], height, len(floors)),
        )
        building_id = cur.lastrowid
        for level, (floor_name, rooms) in enumerate(floors):
            floor_id = conn.execute(
                "INSERT INTO floors (building_id, level, name) VALUES (?,?,?)", (building_id, level, floor_name)
            ).lastrowid
            for code, name, rtype, capacity, monitored in rooms:
                room_id = conn.execute(
                    "INSERT INTO rooms (building_id, floor_id, code, name, room_type, capacity, monitored) VALUES (?,?,?,?,?,?,?)",
                    (building_id, floor_id, code, name, rtype, capacity, int(monitored)),
                ).lastrowid
                room_ids[code] = room_id
                if monitored:
                    _create_simulated_device(conn, room_id, building_id, code, name, rtype, now)
    return room_ids


def _create_simulated_device(conn, room_id, building_id, code, name, rtype, now):
    uid = f"SIM-ESP32-{code}"
    device_id = conn.execute(
        "INSERT INTO devices (device_uid, name, room_id, building_id, is_simulated, created_at) VALUES (?,?,?,?,1,?)",
        (uid, f"Simulated node - {name}", room_id, building_id, now),
    ).lastrowid
    types = ["temperature", "humidity", "occupancy"]
    if rtype in ("classroom", "lab", "seminar", "library", "auditorium", "canteen"):
        types.append("air_quality")
    for t in types:
        unit, mode = SENSOR_DEFS[t]
        conn.execute(
            "INSERT INTO sensors (device_id, room_id, type, unit, sensing_mode) VALUES (?,?,?,?,?)",
            (device_id, room_id, t, unit, mode),
        )


def _seed_rules(conn):
    for name, alert_type, rule_type, sensor_type, op, threshold, severity, desc in cd.DEFAULT_RULES:
        conn.execute(
            "INSERT INTO alert_rules (name, alert_type, rule_type, sensor_type, operator, threshold, severity, description) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (name, alert_type, rule_type, sensor_type, op, threshold, severity, desc),
        )


def _seed_timetable(conn, room_ids):
    """SAMPLE timetable: every class group gets a class in most periods, in a random free room."""
    rng = random.Random(42)
    teaching = conn.execute("SELECT id, room_type FROM rooms WHERE room_type IN ('classroom','lab','seminar')").fetchall()
    theory_rooms = [r["id"] for r in teaching if r["room_type"] != "lab"]
    lab_rooms = [r["id"] for r in teaching if r["room_type"] == "lab"]
    entries = []
    for day in range(0, 6):  # Monday - Saturday
        for start, end in cd.PERIODS:
            used_rooms, used_faculty = set(), set()
            groups = cd.CLASS_GROUPS[:]
            rng.shuffle(groups)
            for group in groups:
                if rng.random() < 0.2:
                    continue
                use_lab = rng.random() < 0.25
                pool = [r for r in (lab_rooms if use_lab else theory_rooms) if r not in used_rooms]
                faculty_pool = [f for f in cd.SAMPLE_FACULTY if f not in used_faculty]
                if not pool or not faculty_pool:
                    continue
                room = rng.choice(pool)
                faculty = rng.choice(faculty_pool)
                used_rooms.add(room)
                used_faculty.add(faculty)
                course = rng.choice(cd.LAB_COURSES if use_lab else cd.THEORY_COURSES)
                entries.append((room, day, start, end, course, faculty, group))
    conn.executemany(
        "INSERT INTO timetable (room_id, day_of_week, start_time, end_time, course, faculty, class_group) VALUES (?,?,?,?,?,?,?)",
        entries,
    )


def _seed_sample_alerts(conn, lab_room_id):
    """A few SAMPLE historical incidents so the incident pages are not empty on first start."""
    now = utcnow()
    admin_names = ("Demo Security Officer",)

    def add(room_code_or_id, alert_type, severity, message, status, minutes_ago, ack_after=None, resolve_after=None):
        room = conn.execute(
            "SELECT r.id, r.building_id, r.floor_id, d.id AS did FROM rooms r LEFT JOIN devices d ON d.room_id = r.id "
            "WHERE r.id = ? OR r.code = ?", (room_code_or_id, str(room_code_or_id))
        ).fetchone()
        if not room:
            return
        created = now - timedelta(minutes=minutes_ago)
        ack = to_iso(created + timedelta(minutes=ack_after)) if ack_after is not None else None
        res = to_iso(created + timedelta(minutes=resolve_after)) if resolve_after is not None else None
        conn.execute(
            "INSERT INTO alerts (alert_type, severity, message, building_id, floor_id, room_id, device_id, status, created_at, "
            "acknowledged_at, acknowledged_by, resolved_at, resolved_by, is_simulated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
            (alert_type, severity, message, room["building_id"], room["floor_id"], room["id"], room["did"], status,
             to_iso(created), ack, admin_names[0] if ack else None, res, admin_names[0] if res else None),
        )

    if lab_room_id:
        add(lab_room_id, "high_temperature", "warning",
            "[Sample history] High temperature (warning): Temperature 35.5°C > 33°C in Lab 204",
            "resolved", 150, ack_after=3, resolve_after=22)
    add("LB0", "high_humidity", "warning",
        "[Sample history] High humidity: Humidity 87.0% > 85% in Reading Hall",
        "acknowledged", 40, ack_after=5)
    add("CL3", "over_capacity", "warning",
        "[Sample history] Over capacity: estimated occupancy 38 exceeds capacity 30 in IoT Lab",
        "resolved", 300, ack_after=2, resolve_after=15)


def reset_db():
    for suffix in ("", "-wal", "-shm"):
        p = Path(DB_PATH + suffix)
        if p.exists():
            p.unlink()


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_db()
        print("Old database removed.")
    init_db()
    with closing(get_conn()) as c:
        created = seed_if_empty(c)
    print("Sample data created." if created else "Database already contains data (use --reset to rebuild).")

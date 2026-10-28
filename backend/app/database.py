"""SQLite connection helper and database schema.

We use Python's built-in sqlite3 module (no ORM) so the whole team can read the SQL.
"""
import sqlite3
from contextlib import closing

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin','faculty','student','operations')),
    class_group TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS buildings (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    x REAL NOT NULL, z REAL NOT NULL,          -- centre on the campus plan (metres, sample)
    width REAL NOT NULL, depth REAL NOT NULL, height REAL NOT NULL,
    floors_count INTEGER NOT NULL,
    is_sample INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS floors (
    id INTEGER PRIMARY KEY,
    building_id INTEGER NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    level INTEGER NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (building_id, level)
);

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY,
    building_id INTEGER NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    floor_id INTEGER NOT NULL REFERENCES floors(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    room_type TEXT NOT NULL,
    capacity INTEGER NOT NULL,
    monitored INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY,
    device_uid TEXT NOT NULL UNIQUE,            -- e.g. ESP32 chip ID / MAC based name
    name TEXT NOT NULL,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    building_id INTEGER NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    is_simulated INTEGER NOT NULL DEFAULT 0,
    last_seen TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS sensors (
    id INTEGER PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    type TEXT NOT NULL,                         -- temperature | humidity | occupancy | air_quality
    unit TEXT,
    sensing_mode TEXT NOT NULL DEFAULT 'value', -- occupancy: 'count' or 'presence'
    last_value REAL,
    last_recorded_at TEXT,
    last_is_simulated INTEGER NOT NULL DEFAULT 0,
    UNIQUE (device_id, type)
);

CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY,
    sensor_id INTEGER NOT NULL REFERENCES sensors(id) ON DELETE CASCADE,
    value REAL NOT NULL,
    recorded_at TEXT NOT NULL,
    is_simulated INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_readings_sensor_time ON readings(sensor_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_readings_time ON readings(recorded_at);

CREATE TABLE IF NOT EXISTS alert_rules (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('threshold','over_capacity','device_offline')),
    sensor_type TEXT,
    operator TEXT NOT NULL DEFAULT '>',
    threshold REAL NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('info','warning','critical')),
    enabled INTEGER NOT NULL DEFAULT 1,
    description TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY,
    rule_id INTEGER REFERENCES alert_rules(id) ON DELETE SET NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    building_id INTEGER REFERENCES buildings(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES floors(id) ON DELETE CASCADE,
    room_id INTEGER REFERENCES rooms(id) ON DELETE CASCADE,
    sensor_id INTEGER REFERENCES sensors(id) ON DELETE SET NULL,
    device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL,
    value REAL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','acknowledged','resolved')),
    created_at TEXT NOT NULL,
    acknowledged_at TEXT, acknowledged_by TEXT,
    resolved_at TEXT, resolved_by TEXT,
    is_simulated INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);

CREATE TABLE IF NOT EXISTS timetable (
    id INTEGER PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL,               -- 0 = Monday ... 6 = Sunday
    start_time TEXT NOT NULL,                   -- HH:MM (IST)
    end_time TEXT NOT NULL,
    course TEXT NOT NULL,
    faculty TEXT,
    class_group TEXT,
    is_sample INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT,
    created_at TEXT NOT NULL,
    is_sample INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT
);
"""


def get_conn() -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may run a request's dependencies and handler in different threads.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    with closing(get_conn()) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def get_db():
    """FastAPI dependency: one connection per request."""
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def rows(cursor) -> list:
    """Convert sqlite3.Row results into plain dicts (JSON friendly)."""
    return [dict(r) for r in cursor.fetchall()]


def one(cursor):
    r = cursor.fetchone()
    return dict(r) if r else None

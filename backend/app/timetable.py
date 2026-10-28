"""Timetable helpers (SAMPLE timetable data - not connected to any official ASIET system)."""
from datetime import datetime, timedelta

from .database import one, rows
from .timeutils import IST, now_ist

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

CLASS_SQL = """
SELECT t.*, r.name AS room_name, r.code AS room_code, r.building_id, r.floor_id
FROM timetable t JOIN rooms r ON r.id = t.room_id
"""


def hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def valid_hhmm(value: str) -> bool:
    try:
        datetime.strptime(value, "%H:%M")
        return True
    except (ValueError, TypeError):
        return False


def active_classes(conn, when: datetime = None) -> dict:
    """{room_id: class row} for classes in session at `when` (IST)."""
    when = when or now_ist()
    cur = conn.execute(
        CLASS_SQL + " WHERE t.day_of_week = ? AND t.start_time <= ? AND t.end_time > ?",
        (when.weekday(), hhmm(when), hhmm(when)),
    )
    return {r["room_id"]: dict(r) for r in cur.fetchall()}


def next_class(conn, room_id: int, when: datetime = None):
    when = when or now_ist()
    for offset in range(0, 7):
        day = when + timedelta(days=offset)
        sql = CLASS_SQL + " WHERE t.room_id = ? AND t.day_of_week = ?"
        params = [room_id, day.weekday()]
        if offset == 0:
            sql += " AND t.start_time > ?"
            params.append(hhmm(when))
        sql += " ORDER BY t.start_time LIMIT 1"
        row = one(conn.execute(sql, params))
        if row:
            row["day_offset"] = offset
            row["day_name"] = DAY_NAMES[row["day_of_week"]]
            return row
    return None


def classes_on_day(conn, day_of_week: int, *, room_id=None, faculty=None, class_group=None):
    sql = CLASS_SQL + " WHERE t.day_of_week = ?"
    params = [day_of_week]
    if room_id is not None:
        sql += " AND t.room_id = ?"
        params.append(room_id)
    if faculty:
        sql += " AND t.faculty = ?"
        params.append(faculty)
    if class_group:
        sql += " AND t.class_group = ?"
        params.append(class_group)
    sql += " ORDER BY t.start_time"
    return rows(conn.execute(sql, params))


def weekly_timetable(conn, *, room_id=None, faculty=None, class_group=None):
    sql = CLASS_SQL + " WHERE 1=1"
    params = []
    if room_id is not None:
        sql += " AND t.room_id = ?"
        params.append(room_id)
    if faculty:
        sql += " AND t.faculty = ?"
        params.append(faculty)
    if class_group:
        sql += " AND t.class_group = ?"
        params.append(class_group)
    sql += " ORDER BY t.day_of_week, t.start_time"
    return rows(conn.execute(sql, params))


def availability(conn, day: datetime, start: str, end: str, room_type=None, min_capacity=0):
    """Rooms that are free / busy in [start, end) on the given date according to the (sample) timetable."""
    sql = (
        "SELECT r.*, b.name AS building_name, b.code AS building_code, f.name AS floor_name, f.level AS floor_level "
        "FROM rooms r JOIN buildings b ON b.id = r.building_id JOIN floors f ON f.id = r.floor_id "
        "WHERE r.capacity >= ?"
    )
    params = [min_capacity or 0]
    if room_type:
        sql += " AND r.room_type = ?"
        params.append(room_type)
    sql += " ORDER BY b.name, f.level, r.name"
    candidates = rows(conn.execute(sql, params))

    busy_rows = conn.execute(
        "SELECT * FROM timetable WHERE day_of_week = ? AND start_time < ? AND end_time > ?",
        (day.weekday(), end, start),
    ).fetchall()
    busy_by_room = {r["room_id"]: dict(r) for r in busy_rows}

    available, busy = [], []
    for room in candidates:
        clash = busy_by_room.get(room["id"])
        if clash:
            room["conflict"] = {
                "course": clash["course"], "start_time": clash["start_time"],
                "end_time": clash["end_time"], "class_group": clash["class_group"],
            }
            busy.append(room)
        else:
            available.append(room)
    return available, busy


def weekly_scheduled_hours(conn):
    """{room_id: scheduled hours per week} from the sample timetable (used for utilisation analytics)."""
    result = {}
    for r in conn.execute("SELECT room_id, start_time, end_time FROM timetable"):
        s = datetime.strptime(r["start_time"], "%H:%M")
        e = datetime.strptime(r["end_time"], "%H:%M")
        result[r["room_id"]] = result.get(r["room_id"], 0.0) + (e - s).total_seconds() / 3600.0
    return result

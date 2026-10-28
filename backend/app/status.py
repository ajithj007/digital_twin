"""Derives device / room / building status from devices and open alerts.

Status values: normal | attention | warning | critical | offline | no_data
  critical / warning : an ACTIVE alert of that severity exists
  offline            : every device in the location has stopped sending data
  attention          : alerts exist that were acknowledged (still open) or are informational
  no_data            : no sensors installed in this location
"""
from collections import defaultdict

from .alert_engine import get_offline_after
from .timeutils import age_seconds, utcnow


def device_is_online(last_seen, offline_after, now=None) -> bool:
    age = age_seconds(last_seen, now)
    return age is not None and age <= offline_after


def _status_from_flags(flags, device_states):
    if flags["critical"]:
        return "critical"
    if flags["warning"]:
        return "warning"
    if not device_states:
        return "no_data"
    if not any(device_states):  # every device offline
        return "offline"
    if flags["attention"]:
        return "attention"
    return "normal"


def compute_location_statuses(conn):
    """Returns {"rooms": {room_id: status}, "buildings": {building_id: status}}."""
    offline_after = get_offline_after(conn)
    now = utcnow()

    room_devices = defaultdict(list)
    building_devices = defaultdict(list)
    for d in conn.execute("SELECT room_id, building_id, last_seen FROM devices"):
        online = device_is_online(d["last_seen"], offline_after, now)
        room_devices[d["room_id"]].append(online)
        building_devices[d["building_id"]].append(online)

    new_flags = lambda: {"critical": 0, "warning": 0, "attention": 0}
    room_flags = defaultdict(new_flags)
    building_flags = defaultdict(new_flags)
    for a in conn.execute(
        "SELECT room_id, building_id, severity, status, alert_type FROM alerts "
        "WHERE status IN ('active','acknowledged')"
    ):
        if a["alert_type"] == "device_offline":
            continue  # offline devices are shown through the 'offline' status instead
        if a["status"] == "active" and a["severity"] in ("critical", "warning"):
            level = a["severity"]
        else:
            level = "attention"
        if a["room_id"] is not None:
            room_flags[a["room_id"]][level] += 1
        if a["building_id"] is not None:
            building_flags[a["building_id"]][level] += 1

    rooms = {}
    for r in conn.execute("SELECT id FROM rooms"):
        rooms[r["id"]] = _status_from_flags(room_flags[r["id"]], room_devices.get(r["id"], []))
    buildings = {}
    for b in conn.execute("SELECT id FROM buildings"):
        buildings[b["id"]] = _status_from_flags(building_flags[b["id"]], building_devices.get(b["id"], []))
    return {"rooms": rooms, "buildings": buildings}


def worst_status(statuses):
    order = ["critical", "warning", "offline", "attention", "normal", "no_data"]
    for s in order:
        if s in statuses:
            return s
    return "no_data"

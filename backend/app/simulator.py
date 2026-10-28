"""Sensor SIMULATOR - generates SIMULATED readings so the system can be demonstrated without hardware.

All readings written here have is_simulated = 1 and the API/UI label them as simulated.
Values follow simple models (time of day, timetable, room occupancy) - this is NOT real sensor data.
Real ESP32 devices use POST /api/ingest instead (is_simulated = 0).
"""
import asyncio
import logging
import math
import random
from contextlib import closing
from datetime import datetime, timedelta

from . import alert_engine, readings, timetable
from .config import (
    MONITOR_INTERVAL_SECONDS, READINGS_RETENTION_HOURS, SIMULATOR_INTERVAL_SECONDS, SIMULATOR_RANDOM_ANOMALIES,
)
from .database import get_conn
from .timeutils import IST, now_ist, to_iso, utcnow, utcnow_iso

log = logging.getLogger("asiet.simulator")

# --- demo controls (in memory; reset when the server restarts) ----------------------
_overrides = {}        # sensor_id -> [value, ticks_left]
_offline_devices = set()  # device ids the simulator stops sending data for


def daily_factor(dt: datetime) -> float:
    """0..1 curve peaking around 15:00 local time."""
    h = dt.hour + dt.minute / 60.0
    return 0.5 + 0.5 * math.sin((h - 9) / 24.0 * 2 * math.pi)


def occupancy_target(room_type: str, capacity: int, dt: datetime, in_class: bool, rng) -> float:
    hour = dt.hour + dt.minute / 60.0
    weekday = dt.weekday() < 6
    if not weekday or hour < 8 or hour >= 18:
        return 0.0
    if room_type in ("classroom", "lab", "seminar"):
        if in_class:
            return capacity * rng.uniform(0.55, 0.9)
        return capacity * rng.uniform(0.0, 0.06)
    if room_type == "library":
        return capacity * rng.uniform(0.2, 0.55)
    if room_type == "canteen":
        return capacity * (rng.uniform(0.6, 0.9) if 12.5 <= hour < 14 else rng.uniform(0.05, 0.25))
    if room_type == "auditorium":
        return capacity * rng.uniform(0.0, 0.08)
    return capacity * rng.uniform(0.1, 0.4)


def target_value(sensor_type: str, ctx: dict, dt: datetime, occupancy: float) -> float:
    if sensor_type == "occupancy":
        return occupancy
    temp = 26.5 + 3.0 * daily_factor(dt) + 0.025 * occupancy
    if sensor_type == "temperature":
        return temp
    if sensor_type == "humidity":
        return max(40.0, min(92.0, 72.0 - 2.2 * (temp - 27.0) + 0.03 * occupancy))
    if sensor_type == "air_quality":  # CO2-equivalent ppm
        return 430.0 + (occupancy / max(ctx["capacity"], 1)) * 850.0
    return 0.0


NOISE = {"temperature": 0.12, "humidity": 0.5, "air_quality": 12.0, "occupancy": 1.2}
SMOOTH = {"temperature": 0.12, "humidity": 0.15, "air_quality": 0.2, "occupancy": 0.3}


def tick(conn, rng=random):
    """One simulation step: write one new SIMULATED reading per sensor (except for 'offline' devices)."""
    now_local = now_ist()
    ts = utcnow_iso()
    classes = timetable.active_classes(conn, now_local)
    rules = alert_engine.load_rules(conn)
    contexts = readings.load_sensor_contexts(conn)
    by_room = {}
    for c in contexts:
        by_room.setdefault(c["room_id"], {})[c["type"]] = c

    touched_devices = set()
    for room_id, sensors in by_room.items():
        sample = next(iter(sensors.values()))
        occ_ctx = sensors.get("occupancy")
        occ_prev = occ_ctx["last_value"] if occ_ctx and occ_ctx["last_value"] is not None else 0.0
        occ_goal = occupancy_target(sample["room_type"], sample["capacity"], now_local, room_id in classes, rng)
        occ_now = max(0.0, occ_prev + (occ_goal - occ_prev) * SMOOTH["occupancy"] + rng.gauss(0, NOISE["occupancy"]))
        if sample["room_type"] in ("classroom", "lab", "seminar") and room_id not in classes and occ_goal < 3:
            occ_now = min(occ_now, 3.0)  # empty between classes

        for stype, ctx in sensors.items():
            if ctx["device_id"] in _offline_devices:
                continue
            override = _overrides.get(ctx["sensor_id"])
            if override:
                value = override[0]
                override[1] -= 1
                if override[1] <= 0:
                    del _overrides[ctx["sensor_id"]]
            else:
                if stype == "occupancy":
                    value = round(occ_now)
                else:
                    goal = target_value(stype, ctx, now_local, occ_now)
                    prev = ctx["last_value"] if ctx["last_value"] is not None else goal
                    value = prev + (goal - prev) * SMOOTH[stype] + rng.gauss(0, NOISE[stype])
                    if SIMULATOR_RANDOM_ANOMALIES and stype == "temperature" and rng.random() < 0.0004:
                        value = 36.0 + rng.random() * 3
            if stype == "humidity":
                value = max(0.0, min(100.0, value))
            readings.record_reading(conn, ctx, round(float(value), 2), is_simulated=True, ts=ts, rules=rules)
            touched_devices.add(ctx["device_id"])
    for device_id in touched_devices:
        readings.touch_device(conn, device_id, ts)
    conn.commit()
    return len(touched_devices)


def backfill(conn, hours=6, step_minutes=5, rng=None, spike=None):
    """Create simulated history so charts are not empty on first start.

    spike: optional (room_id, start_minutes_ago, duration_minutes, value) temperature spike for demo history.
    Returns the generated timestamp list.
    """
    rng = rng or random.Random(7)
    contexts = readings.load_sensor_contexts(conn)
    by_room = {}
    for c in contexts:
        by_room.setdefault(c["room_id"], {})[c["type"]] = c
    now = utcnow()
    steps = int(hours * 60 / step_minutes)
    batch = []
    for i in range(steps, 0, -1):
        t = now - timedelta(minutes=i * step_minutes)
        local = t.astimezone(IST)
        classes = timetable.active_classes(conn, local)
        ts = to_iso(t)
        for room_id, sensors in by_room.items():
            sample = next(iter(sensors.values()))
            occ = occupancy_target(sample["room_type"], sample["capacity"], local, room_id in classes, rng)
            for stype, ctx in sensors.items():
                value = target_value(stype, ctx, local, occ) + rng.gauss(0, NOISE[stype])
                if stype == "occupancy":
                    value = max(0, round(value))
                if stype == "humidity":
                    value = max(0.0, min(100.0, value))
                if spike and stype == "temperature" and ctx["room_id"] == spike[0]:
                    if spike[1] >= i * step_minutes > spike[1] - spike[2]:
                        value = spike[3] + rng.gauss(0, 0.2)
                batch.append((ctx["sensor_id"], round(float(value), 2), ts, 1))
    conn.executemany(
        "INSERT INTO readings (sensor_id, value, recorded_at, is_simulated) VALUES (?,?,?,?)", batch
    )
    # last_value / last_recorded_at come from the newest backfilled point
    conn.execute(
        "UPDATE sensors SET last_value = (SELECT value FROM readings r WHERE r.sensor_id = sensors.id ORDER BY recorded_at DESC LIMIT 1), "
        "last_recorded_at = (SELECT recorded_at FROM readings r WHERE r.sensor_id = sensors.id ORDER BY recorded_at DESC LIMIT 1), "
        "last_is_simulated = 1"
    )
    conn.execute("UPDATE devices SET last_seen = ? WHERE is_simulated = 1", (to_iso(now),))
    conn.commit()
    return len(batch)


def purge_old_readings(conn):
    cutoff = to_iso(utcnow() - timedelta(hours=READINGS_RETENTION_HOURS))
    cur = conn.execute("DELETE FROM readings WHERE recorded_at < ?", (cutoff,))
    conn.commit()
    return cur.rowcount


# --------------------------------------------------------------------------- demo controls
def inject(conn, kind: str, room_id: int):
    """Trigger a SIMULATED event for demonstrations. Returns a short description."""
    ctxs = [c for c in readings.load_sensor_contexts(conn) if c["room_id"] == room_id and c["device_simulated"]]
    if not ctxs:
        raise LookupError("This room has no simulated device")
    by_type = {c["type"]: c for c in ctxs}
    if kind == "high_temperature":
        sensor = by_type.get("temperature")
        if not sensor:
            raise LookupError("No temperature sensor in this room")
        _overrides[sensor["sensor_id"]] = [41.0, 4]
        return f"Simulated 41 C reading in {sensor['room_name']} for the next few updates"
    if kind == "over_capacity":
        sensor = by_type.get("occupancy")
        if not sensor or sensor["sensing_mode"] != "count":
            raise LookupError("No count-mode occupancy sensor in this room")
        _overrides[sensor["sensor_id"]] = [sensor["capacity"] + 10, 4]
        return f"Simulated occupancy of {sensor['capacity'] + 10} (capacity {sensor['capacity']}) in {sensor['room_name']}"
    if kind == "poor_air_quality":
        sensor = by_type.get("air_quality")
        if not sensor:
            raise LookupError("No air-quality sensor in this room")
        _overrides[sensor["sensor_id"]] = [1400.0, 4]
        return f"Simulated 1400 ppm air-quality reading in {sensor['room_name']}"
    if kind in ("device_offline", "device_online"):
        device_id = ctxs[0]["device_id"]
        if kind == "device_offline":
            _offline_devices.add(device_id)
            rule_age = alert_engine.get_offline_after(conn) + 5
            conn.execute("UPDATE devices SET last_seen = ? WHERE id = ?", (to_iso(utcnow() - timedelta(seconds=rule_age)), device_id))
            conn.commit()
            alert_engine.check_devices(conn)
            conn.commit()
            return f"Simulated device {ctxs[0]['device_uid']} going offline"
        _offline_devices.discard(device_id)
        return f"Simulated device {ctxs[0]['device_uid']} back online (next update restores it)"
    raise ValueError(f"Unknown simulation kind '{kind}'")


def status():
    return {
        "active_overrides": len(_overrides),
        "offline_devices": sorted(_offline_devices),
        "interval_seconds": SIMULATOR_INTERVAL_SECONDS,
    }


# --------------------------------------------------------------------------- background loops
def _run_tick():
    with closing(get_conn()) as conn:
        tick(conn)


def _run_monitor(purge: bool):
    with closing(get_conn()) as conn:
        alert_engine.check_devices(conn)
        if purge:
            purge_old_readings(conn)
        conn.commit()


async def run_simulator():
    while True:
        try:
            await asyncio.to_thread(_run_tick)
        except Exception:  # keep the loop alive; the error is logged
            log.exception("simulator tick failed")
        await asyncio.sleep(SIMULATOR_INTERVAL_SECONDS)


async def run_monitor():
    """Evaluates device online/offline status (needed for simulated AND real devices)."""
    counter = 0
    while True:
        try:
            await asyncio.to_thread(_run_monitor, counter % 40 == 0)
        except Exception:
            log.exception("device monitor failed")
        counter += 1
        await asyncio.sleep(MONITOR_INTERVAL_SECONDS)

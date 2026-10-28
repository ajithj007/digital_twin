"""Sensors, raw readings and aggregated series for the monitoring charts."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .. import queries
from ..database import get_db, rows
from ..deps import STAFF, require_roles
from ..timeutils import to_iso, utcnow
from datetime import timedelta

router = APIRouter(tags=["monitoring"])

SENSOR_TYPES = ("temperature", "humidity", "occupancy", "air_quality")
UNITS = {"temperature": "°C", "humidity": "%", "occupancy": "people", "air_quality": "ppm"}


@router.get("/sensors")
def list_sensors(
    building_id: Optional[int] = None,
    floor_id: Optional[int] = None,
    room_id: Optional[int] = None,
    sensor_type: Optional[str] = None,
    user=Depends(require_roles(*STAFF)),
    conn=Depends(get_db),
):
    return queries.sensors_list(conn, building_id, floor_id, room_id, sensor_type)


@router.get("/readings")
def list_readings(
    sensor_id: Optional[int] = None,
    room_id: Optional[int] = None,
    sensor_type: Optional[str] = None,
    minutes: int = 60,
    limit: int = 500,
    user=Depends(require_roles(*STAFF)),
    conn=Depends(get_db),
):
    since = to_iso(utcnow() - timedelta(minutes=max(1, min(minutes, 24 * 60))))
    sql = (
        "SELECT rd.id, rd.sensor_id, s.type AS sensor_type, s.room_id, rd.value, rd.recorded_at, rd.is_simulated "
        "FROM readings rd JOIN sensors s ON s.id = rd.sensor_id WHERE rd.recorded_at >= ?"
    )
    params = [since]
    for column, value in (("rd.sensor_id", sensor_id), ("s.room_id", room_id), ("s.type", sensor_type)):
        if value is not None:
            sql += f" AND {column} = ?"
            params.append(value)
    sql += " ORDER BY rd.recorded_at DESC LIMIT ?"
    params.append(max(1, min(limit, 2000)))
    return rows(conn.execute(sql, params))


@router.get("/monitoring/series")
def monitoring_series(
    sensor_type: str,
    minutes: int = 60,
    building_id: Optional[int] = None,
    floor_id: Optional[int] = None,
    room_id: Optional[int] = None,
    user=Depends(require_roles(*STAFF)),
    conn=Depends(get_db),
):
    if sensor_type not in SENSOR_TYPES:
        raise HTTPException(status_code=422, detail=f"sensor_type must be one of {', '.join(SENSOR_TYPES)}")
    points = queries.build_series(
        conn, sensor_type=sensor_type, minutes=minutes, building_id=building_id, floor_id=floor_id, room_id=room_id
    )
    return {
        "sensor_type": sensor_type,
        "unit": UNITS[sensor_type],
        "minutes": minutes,
        "points": points,
        "thresholds": queries.thresholds_for(conn, sensor_type),
        "aggregation_note": "Average across the selected sensors (occupancy also provides 'sum').",
    }

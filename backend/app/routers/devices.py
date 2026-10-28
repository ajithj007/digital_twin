"""IoT device management and the ESP32 ingestion endpoint."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .. import queries, readings
from ..audit import log_audit
from ..database import get_db, one
from ..deps import ADMIN, OPS, require_roles, verify_device_key
from ..schemas import DeviceCreate, IngestPayload
from ..timeutils import utcnow_iso

router = APIRouter(tags=["devices"])

ALLOWED_SENSOR_TYPES = tuple(readings.VALID_RANGES.keys())


@router.get("/devices")
def list_devices(
    building_id: Optional[int] = None,
    status: Optional[str] = None,
    user=Depends(require_roles(*OPS)),
    conn=Depends(get_db),
):
    return queries.devices_list(conn, building_id=building_id, status=status)


@router.get("/devices/{device_id}")
def get_device(device_id: int, user=Depends(require_roles(*OPS)), conn=Depends(get_db)):
    device = queries.device_detail(conn, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("/devices", status_code=201)
def register_device(body: DeviceCreate, user=Depends(require_roles(*ADMIN)), conn=Depends(get_db)):
    """Register a real ESP32 device and its sensors (maps device -> room)."""
    room = one(conn.execute("SELECT id, building_id FROM rooms WHERE id = ?", (body.room_id,)))
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if one(conn.execute("SELECT id FROM devices WHERE device_uid = ?", (body.device_uid,))):
        raise HTTPException(status_code=409, detail="A device with this ID already exists")
    for s in body.sensors:
        if s.type not in ALLOWED_SENSOR_TYPES:
            raise HTTPException(status_code=422, detail=f"Unsupported sensor type '{s.type}'")
    device_id = conn.execute(
        "INSERT INTO devices (device_uid, name, room_id, building_id, is_simulated, created_at) VALUES (?,?,?,?,0,?)",
        (body.device_uid, body.name, room["id"], room["building_id"], utcnow_iso()),
    ).lastrowid
    for s in body.sensors:
        conn.execute(
            "INSERT INTO sensors (device_id, room_id, type, unit, sensing_mode) VALUES (?,?,?,?,?)",
            (device_id, room["id"], s.type, s.unit, s.sensing_mode),
        )
    log_audit(conn, user["name"], "device_registered", body.device_uid)
    conn.commit()
    return queries.device_detail(conn, device_id)


@router.post("/ingest")
def ingest(body: IngestPayload, device_ok=Depends(verify_device_key), conn=Depends(get_db)):
    """ESP32 endpoint. Header: X-Device-Key. Readings are stored with is_simulated = 0."""
    device = one(conn.execute("SELECT * FROM devices WHERE device_uid = ?", (body.device_uid,)))
    if not device:
        raise HTTPException(status_code=404, detail="Unknown device_uid - register the device first (POST /api/devices)")
    accepted, rejected = readings.ingest_payload(conn, device, [r.model_dump() for r in body.readings])
    conn.commit()
    if accepted == 0 and rejected:
        raise HTTPException(status_code=422, detail={"message": "No valid readings", "rejected": rejected})
    return {"device_uid": body.device_uid, "accepted": accepted, "rejected": rejected, "received_at": utcnow_iso()}

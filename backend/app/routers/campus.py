"""Buildings, floors, rooms (campus hierarchy)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .. import queries
from ..database import get_db
from ..deps import ALL_ROLES, STAFF, require_roles

router = APIRouter(tags=["campus"])


@router.get("/buildings")
def list_buildings(user=Depends(require_roles(*ALL_ROLES)), conn=Depends(get_db)):
    return queries.buildings_overview(conn)


@router.get("/buildings/{building_id}")
def get_building(building_id: int, user=Depends(require_roles(*ALL_ROLES)), conn=Depends(get_db)):
    building = queries.building_detail(conn, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.get("/rooms")
def list_rooms(
    building_id: Optional[int] = None,
    floor_id: Optional[int] = None,
    room_type: Optional[str] = None,
    user=Depends(require_roles(*ALL_ROLES)),
    conn=Depends(get_db),
):
    return queries.rooms_overview(conn, building_id=building_id, floor_id=floor_id, room_type=room_type)


@router.get("/rooms/{room_id}")
def get_room(room_id: int, user=Depends(require_roles(*ALL_ROLES)), conn=Depends(get_db)):
    room = queries.room_detail(conn, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if user["role"] == "student":  # students do not see sensor-level details
        room["sensors"] = []
        room["alerts"] = [a for a in room["alerts"] if a["status"] == "active" and a["severity"] in ("warning", "critical")]
    return room


@router.get("/rooms/{room_id}/history")
def room_history(room_id: int, minutes: int = 120, user=Depends(require_roles(*STAFF)), conn=Depends(get_db)):
    if not queries.rooms_overview(conn, room_id=room_id):
        raise HTTPException(status_code=404, detail="Room not found")
    return {
        "minutes": minutes,
        **{t: queries.build_series(conn, sensor_type=t, minutes=minutes, room_id=room_id)
           for t in ("temperature", "humidity", "occupancy", "air_quality")},
    }

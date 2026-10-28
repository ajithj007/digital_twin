"""Timetable and room availability (SAMPLE timetable data)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .. import timetable as tt
from ..database import get_db
from ..deps import ALL_ROLES, require_roles
from ..timeutils import now_ist

router = APIRouter(prefix="/timetable", tags=["timetable"])


@router.get("")
def get_timetable(
    room_id: Optional[int] = None,
    faculty: Optional[str] = None,
    class_group: Optional[str] = None,
    user=Depends(require_roles(*ALL_ROLES)),
    conn=Depends(get_db),
):
    entries = tt.weekly_timetable(conn, room_id=room_id, faculty=faculty, class_group=class_group)
    return {"is_sample": True, "entries": entries, "day_names": tt.DAY_NAMES}


@router.get("/groups")
def get_groups(user=Depends(require_roles(*ALL_ROLES)), conn=Depends(get_db)):
    groups = [r["class_group"] for r in conn.execute("SELECT DISTINCT class_group FROM timetable ORDER BY class_group")]
    faculty = [r["faculty"] for r in conn.execute("SELECT DISTINCT faculty FROM timetable ORDER BY faculty")]
    return {"class_groups": groups, "faculty": faculty}


@router.get("/availability")
def room_availability(
    day: Optional[str] = None,          # YYYY-MM-DD (default: today, IST)
    start: Optional[str] = None,        # HH:MM
    end: Optional[str] = None,          # HH:MM
    room_type: Optional[str] = None,
    min_capacity: int = 0,
    user=Depends(require_roles(*ALL_ROLES)),
    conn=Depends(get_db),
):
    now = now_ist()
    try:
        date = datetime.strptime(day, "%Y-%m-%d") if day else now
    except ValueError:
        raise HTTPException(status_code=422, detail="day must be YYYY-MM-DD")
    start = start or now.strftime("%H:%M")
    end = end or "23:59"
    if not (tt.valid_hhmm(start) and tt.valid_hhmm(end)):
        raise HTTPException(status_code=422, detail="start and end must be HH:MM")
    if start >= end:
        raise HTTPException(status_code=422, detail="end must be later than start")
    available, busy = tt.availability(conn, date, start, end, room_type, min_capacity)
    return {
        "is_sample": True,
        "day": date.strftime("%Y-%m-%d"),
        "day_name": tt.DAY_NAMES[date.weekday()],
        "start": start,
        "end": end,
        "available": available,
        "busy": busy,
        "note": "Availability is based on the SAMPLE timetable only; it is not connected to ASIET's official timetable.",
    }

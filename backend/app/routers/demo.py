"""Demo controls for the SIMULATOR (trigger simulated events). Not available for real devices."""
from fastapi import APIRouter, Depends, HTTPException

from .. import simulator
from ..audit import log_audit
from ..config import SIMULATOR_ENABLED
from ..database import get_db
from ..deps import OPS, require_roles
from ..schemas import InjectRequest

router = APIRouter(prefix="/simulator", tags=["simulator"])


@router.get("/status")
def simulator_status(user=Depends(require_roles(*OPS))):
    return {"enabled": SIMULATOR_ENABLED, **simulator.status()}


@router.post("/inject")
def inject(body: InjectRequest, user=Depends(require_roles(*OPS)), conn=Depends(get_db)):
    if not SIMULATOR_ENABLED:
        raise HTTPException(status_code=409, detail="The simulator is disabled (SIMULATOR_ENABLED=0)")
    try:
        message = simulator.inject(conn, body.kind, body.room_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    log_audit(conn, user["name"], "simulation_triggered", f"{body.kind} room #{body.room_id}")
    conn.commit()
    return {"message": message, "simulated": True}

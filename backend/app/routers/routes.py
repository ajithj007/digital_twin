"""Campus navigation (graph based, prototype)."""
from fastapi import APIRouter, Depends, HTTPException

from .. import navigation
from ..database import get_db
from ..deps import ALL_ROLES, require_roles

router = APIRouter(prefix="/navigation", tags=["navigation"])


@router.get("/map")
def navigation_map(user=Depends(require_roles(*ALL_ROLES))):
    return navigation.nav_map()


@router.get("/locations")
def navigation_locations(user=Depends(require_roles(*ALL_ROLES)), conn=Depends(get_db)):
    return navigation.list_locations(conn)


@router.get("/route")
def navigation_route(source: str, destination: str, user=Depends(require_roles(*ALL_ROLES)), conn=Depends(get_db)):
    """source / destination look like 'node:main_gate', 'building:3' or 'room:12'."""
    try:
        return navigation.compute_route(conn, source, destination)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

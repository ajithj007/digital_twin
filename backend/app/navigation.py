"""Campus navigation: Dijkstra shortest path over a predefined walking graph.

The graph (campus_data.NAV_NODES / NAV_EDGES) is SAMPLE data. Routes are outdoor routes between
building entrances. Indoor navigation is NOT implemented: for rooms above the ground floor we only
report a floor transition ("take stairs/lift to Floor N").
"""
import heapq
import math

from .campus_data import NAV_EDGES, NAV_NODES
from .config import SECONDS_PER_FLOOR_TRANSITION, WALKING_SPEED_M_PER_S
from .database import one, rows


def _build_graph():
    graph = {k: [] for k in NAV_NODES}
    for a, b, kind in NAV_EDGES:
        _, ax, az, _ = NAV_NODES[a]
        _, bx, bz, _ = NAV_NODES[b]
        dist = math.hypot(ax - bx, az - bz)
        graph[a].append((b, dist))
        graph[b].append((a, dist))
    return graph


GRAPH = _build_graph()


def dijkstra(start: str, goal: str):
    """Returns (distance_m, [node keys]) or (None, []) when unreachable."""
    if start not in GRAPH or goal not in GRAPH:
        return None, []
    queue = [(0.0, start)]
    best = {start: 0.0}
    previous = {}
    while queue:
        dist, node = heapq.heappop(queue)
        if node == goal:
            path = [goal]
            while path[-1] in previous:
                path.append(previous[path[-1]])
            return dist, list(reversed(path))
        if dist > best.get(node, math.inf):
            continue
        for neighbour, weight in GRAPH[node]:
            candidate = dist + weight
            if candidate < best.get(neighbour, math.inf):
                best[neighbour] = candidate
                previous[neighbour] = node
                heapq.heappush(queue, (candidate, neighbour))
    return None, []


def nav_map():
    nodes = [
        {"key": k, "name": v[0], "x": v[1], "z": v[2], "kind": v[3]} for k, v in NAV_NODES.items()
    ]
    edges = [{"a": a, "b": b, "kind": kind} for a, b, kind in NAV_EDGES]
    return {"nodes": nodes, "edges": edges, "is_sample": True}


def list_locations(conn):
    """Everything the user can pick as source/destination: key looks like 'node:main_gate', 'building:3', 'room:12'."""
    out = []
    for k, v in NAV_NODES.items():
        if v[3] in ("gate", "parking"):
            out.append({"key": f"node:{k}", "label": v[0], "type": "place", "group": "Campus places"})
    for b in rows(conn.execute("SELECT id, name FROM buildings ORDER BY id")):
        out.append({"key": f"building:{b['id']}", "label": b["name"], "type": "building", "group": "Buildings"})
    for r in rows(conn.execute(
        "SELECT r.id, r.name, b.name AS bname, f.name AS fname FROM rooms r "
        "JOIN buildings b ON b.id = r.building_id JOIN floors f ON f.id = r.floor_id ORDER BY b.id, f.level, r.id"
    )):
        out.append({"key": f"room:{r['id']}", "label": f"{r['name']} ({r['bname']}, {r['fname']})", "type": "room", "group": "Rooms"})
    return out


def resolve_location(conn, key: str):
    """Map a location key to a graph node + descriptive info. Raises ValueError for unknown keys."""
    kind, _, ident = (key or "").partition(":")
    if kind == "node" and ident in NAV_NODES:
        return {"node": ident, "label": NAV_NODES[ident][0], "building": None, "floor_level": 0, "floor_name": None}
    if kind == "building" and ident.isdigit():
        b = one(conn.execute("SELECT id, code, name FROM buildings WHERE id = ?", (int(ident),)))
        if b and f"entrance_{b['code'].lower()}" in NAV_NODES:
            return {"node": f"entrance_{b['code'].lower()}", "label": b["name"], "building": b["name"],
                    "building_id": b["id"], "floor_level": 0, "floor_name": None}
    if kind == "room" and ident.isdigit():
        r = one(conn.execute(
            "SELECT r.id, r.name, r.building_id, b.code, b.name AS bname, f.level, f.name AS fname, r.floor_id "
            "FROM rooms r JOIN buildings b ON b.id = r.building_id JOIN floors f ON f.id = r.floor_id WHERE r.id = ?",
            (int(ident),)))
        if r and f"entrance_{r['code'].lower()}" in NAV_NODES:
            return {"node": f"entrance_{r['code'].lower()}", "label": r["name"], "building": r["bname"],
                    "building_id": r["building_id"], "floor_id": r["floor_id"], "room_id": r["id"],
                    "floor_level": r["level"], "floor_name": r["fname"]}
    raise ValueError(f"Unknown location '{key}'")


def compute_route(conn, source_key: str, destination_key: str):
    src = resolve_location(conn, source_key)
    dst = resolve_location(conn, destination_key)
    distance, path = dijkstra(src["node"], dst["node"])
    if distance is None:
        raise LookupError("No walking route found between these locations")

    points = [{"key": k, "name": NAV_NODES[k][0], "x": NAV_NODES[k][1], "z": NAV_NODES[k][2], "kind": NAV_NODES[k][3]} for k in path]

    steps = [f"Start at {src['label']}" + (f" (Floor: {src['floor_name']})" if src.get("floor_level") else "")]
    if src.get("floor_level"):
        steps.append(f"Go down to the ground floor of {src['building']}")
    pending = 0.0
    for i in range(1, len(path)):
        seg = next(w for n, w in GRAPH[path[i - 1]] if n == path[i])
        node_kind = NAV_NODES[path[i]][3]
        if node_kind == "junction" and i != len(path) - 1:
            pending += seg
            continue
        total = pending + seg
        pending = 0.0
        if node_kind == "junction":
            steps.append(f"Continue along the road for about {round(total)} m")
        else:
            steps.append(f"Walk about {round(total)} m to {NAV_NODES[path[i]][0]}")
    if len(path) == 1:
        steps.append("You are already at this location's entrance")

    floor_transitions = []
    if dst.get("floor_level"):
        floor_transitions.append({
            "building": dst["building"], "to_level": dst["floor_level"], "to_floor": dst["floor_name"],
            "instruction": f"Take the stairs/lift to {dst['floor_name']} in {dst['building']}",
        })
        steps.append(floor_transitions[0]["instruction"])
    steps.append(f"Arrive at {dst['label']}")

    extra_seconds = abs(dst.get("floor_level", 0)) * SECONDS_PER_FLOOR_TRANSITION
    walk_seconds = distance / WALKING_SPEED_M_PER_S + extra_seconds
    buildings = [b for b in (src.get("building"), dst.get("building")) if b]
    return {
        "source": {"key": source_key, "label": src["label"]},
        "destination": {"key": destination_key, "label": dst["label"], "floor_name": dst.get("floor_name"),
                        "building_id": dst.get("building_id"), "floor_id": dst.get("floor_id"), "room_id": dst.get("room_id")},
        "path": points,
        "distance_m": round(distance),
        "walking_time_min": max(1, round(walk_seconds / 60)),
        "buildings": list(dict.fromkeys(buildings)),
        "floor_transitions": floor_transitions,
        "steps": steps,
        "note": ("Prototype route on predefined SAMPLE pathways (outdoor only). Distances are approximate; "
                 f"time assumes {WALKING_SPEED_M_PER_S} m/s walking and {SECONDS_PER_FLOOR_TRANSITION} s per floor. "
                 "Indoor navigation is not implemented."),
    }

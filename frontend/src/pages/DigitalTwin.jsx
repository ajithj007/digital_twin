import { useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import ErrorBoundary from "../components/ErrorBoundary.jsx";
import { Card, DataState, ErrorBox, LiveIndicator, Loading, PageHeader } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { shortName } from "../utils/format.js";
import CampusScene from "../three/CampusScene.jsx";
import { BuildingPanel, CampusPanel, FloorPanel, RoomPanel, StatusLegend } from "./twin/Panels.jsx";

const toNum = (v) => (v ? Number(v) : null);

export default function DigitalTwin() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const buildingId = toNum(params.get("building"));
  const floorId = toNum(params.get("floor"));
  const roomId = toNum(params.get("room"));
  const alertId = params.get("alert");

  // the URL is the single source of truth, so links from search / incidents / room availability just work
  const go = (next) => {
    const p = new URLSearchParams();
    if (next.building) p.set("building", next.building);
    if (next.floor) p.set("floor", next.floor);
    if (next.room) p.set("room", next.room);
    if (next.alert) p.set("alert", next.alert);
    setParams(p);
  };

  const buildings = useApi(() => api.buildings(), [], { interval: 5000 });
  const navMap = useApi(() => api.navMap(), []);
  const detail = useApi(() => api.building(buildingId), [buildingId], { interval: 5000, enabled: !!buildingId });
  const room = useApi(() => api.room(roomId), [roomId], { interval: 5000, enabled: !!roomId });

  const detailData = detail.data && detail.data.id === buildingId ? detail.data : null;
  const roomData = room.data && room.data.id === roomId ? room.data : null;
  const floorData = detailData && floorId ? detailData.floors.find((f) => f.id === floorId) : null;

  // a link that only contains ?room=ID: fill in building and floor from the room
  useEffect(() => {
    if (roomData && (!buildingId || !floorId)) go({ building: roomData.building_id, floor: roomData.floor_id, room: roomData.id, alert: alertId });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomData?.id]);

  const level = roomId ? "room" : floorId ? "floor" : buildingId ? "building" : "campus";
  const building = buildings.data?.find((b) => b.id === buildingId);

  const crumbs = [{ label: "Campus", onClick: () => go({}) }];
  if (buildingId) crumbs.push({ label: building ? shortName(building.name) : "Building", onClick: () => go({ building: buildingId }) });
  if (floorId) crumbs.push({ label: floorData?.name || "Floor", onClick: () => go({ building: buildingId, floor: floorId }) });
  if (roomId) crumbs.push({ label: roomData?.name || "Room" });

  return (
    <>
      <PageHeader
        title="Digital Twin"
        subtitle="Interactive 3D model of the campus (sample layout) linked to sensor data, alerts and rooms."
        actions={<LiveIndicator updatedAt={buildings.updatedAt} loading={buildings.loading} />}
      />

      <nav className="breadcrumbs" aria-label="Location">
        {crumbs.map((c, i) => (
          <span key={i}>
            {i > 0 && <span className="sep">›</span>}
            {c.onClick && i < crumbs.length - 1 ? <button className="crumb" onClick={c.onClick}>{c.label}</button> : <span className="crumb current">{c.label}</span>}
          </span>
        ))}
      </nav>

      {alertId && (
        <div className="info-banner">
          Showing the location of incident #{alertId}. <Link to={`/incidents?highlight=${alertId}`}>Back to the incident</Link>
        </div>
      )}

      <div className="twin-layout">
        <div>
          <Card padded={false}>
            {buildings.loading && !buildings.data && <Loading text="Loading campus…" />}
            {buildings.error && !buildings.data && <ErrorBox error={buildings.error} onRetry={buildings.reload} />}
            {buildings.data && (
              <ErrorBoundary title="The 3D view could not be started." hint="Your browser or graphics driver may not support WebGL. The building list on the right still works.">
                <CampusScene
                  buildings={buildings.data}
                  detail={detailData}
                  navMap={navMap.data}
                  selectedBuildingId={buildingId}
                  selectedFloorId={floorId}
                  selectedRoomId={roomId}
                  highlightBuildingId={alertId ? buildingId : null}
                  onSelectBuilding={(b) => go({ building: b.id })}
                  onSelectFloor={(f) => go({ building: buildingId, floor: f.id })}
                  onSelectRoom={(r) => go({ building: buildingId, floor: floorId, room: r.id })}
                  height={560}
                />
              </ErrorBoundary>
            )}
          </Card>
          <StatusLegend />
          <p className="muted small">Drag to rotate · scroll to zoom · right-drag to pan · click a building, floor or room. Building positions and sizes are a SAMPLE layout.</p>
        </div>

        <div className="stack">
          {level === "campus" && buildings.data && <CampusPanel buildings={buildings.data} onSelect={(b) => go({ building: b.id })} />}
          {level !== "campus" && (
            <DataState result={detail}>
              {(d) => {
                if (d.id !== buildingId) return <Loading />;
                if (level === "building") return <BuildingPanel detail={d} onSelectFloor={(f) => go({ building: buildingId, floor: f.id })} />;
                if (level === "floor" && floorData) return <FloorPanel detail={d} floor={floorData} onSelectRoom={(r) => go({ building: buildingId, floor: floorId, room: r.id })} />;
                if (level === "room") return roomData ? <RoomPanel room={roomData} /> : <DataState result={room}>{() => <Loading />}</DataState>;
                return <ErrorBox error={{ message: "This floor was not found in the building." }} />;
              }}
            </DataState>
          )}
          {level !== "campus" && (
            <button className="btn btn-ghost" onClick={() => navigate(-1)}>← Back</button>
          )}
        </div>
      </div>
    </>
  );
}

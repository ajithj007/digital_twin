import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import CampusMap2D from "../components/CampusMap2D.jsx";
import ErrorBoundary from "../components/ErrorBoundary.jsx";
import { Card, DataState, ErrorBox, Loading, PageHeader, StatCard, Tabs } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import CampusScene from "../three/CampusScene.jsx";
import { twinLink } from "../utils/format.js";

function LocationSelect({ label, value, onChange, locations }) {
  const groups = useMemo(() => {
    const g = {};
    (locations || []).forEach((l) => { (g[l.group] = g[l.group] || []).push(l); });
    return g;
  }, [locations]);
  return (
    <label className="field"><span>{label}</span>
      <select className="select" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Select…</option>
        {Object.entries(groups).map(([g, items]) => (
          <optgroup key={g} label={g}>{items.map((l) => <option key={l.key} value={l.key}>{l.label}</option>)}</optgroup>
        ))}
      </select>
    </label>
  );
}

export default function Navigation() {
  const [params, setParams] = useSearchParams();
  const [source, setSource] = useState(params.get("source") || "node:main_gate");
  const [destination, setDestination] = useState(params.get("destination") || "");
  const [route, setRoute] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState("2d");

  const locations = useApi(() => api.navLocations(), []);
  const navMap = useApi(() => api.navMap(), []);
  const buildings = useApi(() => api.buildings(), [], { interval: 10000 });

  const findRoute = async (src = source, dst = destination) => {
    if (!src || !dst) { setError({ message: "Please choose both a start and a destination." }); return; }
    setBusy(true); setError(null);
    try {
      setRoute(await api.route(src, dst));
      setParams({ source: src, destination: dst }, { replace: true });
    } catch (e) { setError(e); setRoute(null); } finally { setBusy(false); }
  };

  // opened from "Navigate" buttons elsewhere: ?destination=room:12
  useEffect(() => {
    if (params.get("destination")) findRoute(source, params.get("destination"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dest = route?.destination;
  return (
    <>
      <PageHeader title="Campus Navigation" subtitle="Shortest walking route on predefined (sample) campus pathways, computed with Dijkstra's algorithm." />
      <Card>
        <div className="filters">
          <LocationSelect label="From" value={source} onChange={setSource} locations={locations.data} />
          <button className="btn btn-ghost" onClick={() => { setSource(destination); setDestination(source); }} title="Swap">⇄</button>
          <LocationSelect label="To" value={destination} onChange={setDestination} locations={locations.data} />
          <button className="btn btn-primary" onClick={() => findRoute()} disabled={busy}>{busy ? "Finding…" : "Find route"}</button>
        </div>
        {locations.error && <ErrorBox error={locations.error} onRetry={locations.reload} />}
        {error && <div className="error-box" role="alert">{error.message}</div>}
      </Card>

      <div className="twin-layout">
        <Card title="Map" actions={<Tabs value={view} onChange={setView} tabs={[{ value: "2d", label: "2D map" }, { value: "3d", label: "3D view" }]} />} padded={false}>
          {(!buildings.data || !navMap.data) ? <Loading /> : view === "2d" ? (
            <CampusMap2D buildings={buildings.data} navMap={navMap.data} route={route?.path} highlightBuildingId={dest?.building_id} height={460} />
          ) : (
            <ErrorBoundary title="The 3D view could not be started.">
              <CampusScene buildings={buildings.data} navMap={navMap.data} route={route?.path} height={460} interactive={false} />
            </ErrorBoundary>
          )}
          <div className="map-legend small muted"><span className="dot" style={{ background: "#16a34a" }} /> start <span className="dot" style={{ background: "#dc2626" }} /> destination <span className="dot" style={{ background: "#2563eb" }} /> route</div>
        </Card>

        <div className="stack">
          {!route && <Card><p className="muted">Choose a start and a destination, then press “Find route”. Try From “Main Gate” to “Lab 204”.</p></Card>}
          {route && (
            <>
              <div className="grid grid-3">
                <StatCard label="Distance" value={`${route.distance_m} m`} hint="approximate" />
                <StatCard label="Walking time" value={`${route.walking_time_min} min`} hint="estimate" />
                <StatCard label="Floor changes" value={route.floor_transitions.length} />
              </div>
              <Card title="Directions">
                <ol className="steps">{route.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
                {route.buildings.length > 0 && <p className="small"><strong>Buildings:</strong> {route.buildings.join(", ")}</p>}
                {route.floor_transitions.map((f, i) => <p key={i} className="small"><strong>Floor transition:</strong> {f.instruction}</p>)}
                <div className="row wrap">
                  {dest?.building_id && <Link className="btn btn-sm" to={twinLink({ building_id: dest.building_id, floor_id: dest.floor_id, room_id: dest.room_id })}>View destination on Digital Twin</Link>}
                </div>
                <p className="muted small">{route.note}</p>
              </Card>
            </>
          )}
        </div>
      </div>
    </>
  );
}

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../../api/client.js";
import ErrorBoundary from "../../components/ErrorBoundary.jsx";
import { AlertStatusBadge, Card, EmptyState, SeverityBadge, StatusBadge } from "../../components/ui.jsx";
import CampusScene from "../../three/CampusScene.jsx";
import { ALERT_TYPE_LABELS } from "../../utils/constants.js";
import { alertLocation, relativeTime, shortName, twinLink } from "../../utils/format.js";

export function TwinPreview({ buildings, navMap, height = 360 }) {
  const navigate = useNavigate();
  return (
    <Card title="Campus Digital Twin" actions={<Link className="btn btn-sm" to="/twin">Open full view</Link>} padded={false}>
      <ErrorBoundary title="The 3D view could not be started." hint="WebGL may be unavailable. Use the Digital Twin page or the building list.">
        <CampusScene buildings={buildings} navMap={navMap} height={height} onSelectBuilding={(b) => navigate(twinLink({ building_id: b.id }))} />
      </ErrorBoundary>
    </Card>
  );
}

export function BuildingStatusList({ buildings }) {
  return (
    <Card title="Building status" padded={false}>
      <div className="list">
        {buildings.map((b) => (
          <Link key={b.id} className="list-item" to={twinLink({ building_id: b.id })}>
            <div className="grow">
              <div className="strong">{shortName(b.name)}</div>
              <div className="muted small">{b.occupancy_pct === null ? "no occupancy data" : `${b.occupancy} people · ${b.occupancy_pct}% of monitored capacity`}</div>
            </div>
            <StatusBadge status={b.status} />
          </Link>
        ))}
      </div>
    </Card>
  );
}

/** Compact incident list with acknowledge / resolve buttons (only when canAct). */
export function IncidentList({ alerts, canAct, onChanged, title = "Recent incidents" }) {
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const act = async (fn, id) => {
    setBusy(id);
    setError("");
    try {
      await fn(id);
      onChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <Card title={title} actions={<Link className="btn btn-sm btn-ghost" to="/incidents">All incidents</Link>} padded={false}>
      {error && <div className="error-box">{error}</div>}
      {alerts.length === 0 && <EmptyState>No incidents to show.</EmptyState>}
      <div className="list">
        {alerts.map((a) => (
          <div key={a.id} className="list-item static">
            <div className="grow">
              <div className="row wrap"><SeverityBadge severity={a.severity} /><AlertStatusBadge status={a.status} /><span className="strong">{ALERT_TYPE_LABELS[a.alert_type] || a.alert_type}</span></div>
              <div className="small">{a.message}</div>
              <div className="muted small">{alertLocation(a)} · {relativeTime(a.created_at)}</div>
            </div>
            <div className="row wrap">
              <Link className="btn btn-sm" to={twinLink({ building_id: a.building_id, floor_id: a.floor_id, room_id: a.room_id, id: a.id })}>View on twin</Link>
              {canAct && a.status === "active" && <button className="btn btn-sm" disabled={busy === a.id} onClick={() => act(api.acknowledge, a.id)}>Acknowledge</button>}
              {canAct && a.status !== "resolved" && <button className="btn btn-sm btn-primary" disabled={busy === a.id} onClick={() => act(api.resolve, a.id)}>Resolve</button>}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function ClassTable({ classes, empty = "No classes today." }) {
  if (!classes?.length) return <EmptyState>{empty}</EmptyState>;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead><tr><th>Time</th><th>Course</th><th>Room</th><th>Group</th><th>Faculty</th></tr></thead>
        <tbody>
          {classes.map((c) => (
            <tr key={c.id}>
              <td>{c.start_time}-{c.end_time}</td>
              <td>{c.course}</td>
              <td><Link to={twinLink({ building_id: c.building_id, floor_id: c.floor_id, room_id: c.room_id })}>{c.room_name}</Link></td>
              <td>{c.class_group}</td>
              <td>{c.faculty}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function FreeRooms({ rooms }) {
  if (!rooms?.length) return <EmptyState>No free rooms found for the next hour.</EmptyState>;
  return (
    <div className="list">
      {rooms.map((r) => (
        <div key={r.id} className="list-item static">
          <div className="grow"><div className="strong">{r.name}</div><div className="muted small">{shortName(r.building_name)} · {r.floor_name} · capacity {r.capacity}</div></div>
          <Link className="btn btn-sm" to={twinLink({ building_id: r.building_id, floor_id: r.floor_id, room_id: r.id })}>View</Link>
          <Link className="btn btn-sm" to={`/navigation?destination=room:${r.id}`}>Navigate</Link>
        </div>
      ))}
    </div>
  );
}

export function CampusStatusBanner({ status, active }) {
  const text = status === "critical" ? "Critical conditions reported" : status === "warning" ? "Warnings active" : status === "attention" ? "Some items need attention" : status === "offline" ? "Devices offline" : "All monitored locations normal";
  return (
    <div className={`status-banner status-${status}`}>
      <StatusBadge status={status} /> <strong>{text}</strong> <span className="muted">· {active} active incident{active === 1 ? "" : "s"}</span>
    </div>
  );
}

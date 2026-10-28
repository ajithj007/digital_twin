import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import { AlertStatusBadge, Card, DataState, EmptyState, LiveIndicator, PageHeader, SeverityBadge, SimulatedTag } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useMeta } from "../context/MetaContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { ALERT_TYPE_LABELS, OPS } from "../utils/constants.js";
import { alertLocation, fmtDateTime, fmtNum, twinLink } from "../utils/format.js";

function DemoControls({ onDone }) {
  const rooms = useApi(() => api.rooms({}), []);
  const [roomId, setRoomId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const monitored = (rooms.data || []).filter((r) => r.has_sensors);
  const run = async (kind) => {
    setError(""); setMessage("");
    try {
      const res = await api.inject(kind, Number(roomId || monitored[0]?.id));
      setMessage(`${res.message}. The alert appears after the next simulator update (about 10 s).`);
      setTimeout(onDone, 1500);
    } catch (e) { setError(e.message); }
  };
  return (
    <Card title="Demo controls (simulator only)">
      <p className="muted small">Trigger SIMULATED events to demonstrate the alert rules. These do not represent real incidents.</p>
      <div className="filters">
        <label className="field"><span>Room</span>
          <select className="select" value={roomId} onChange={(e) => setRoomId(e.target.value)}>
            <option value="">{monitored[0] ? `${monitored[0].name} (default)` : "Loading…"}</option>
            {monitored.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select></label>
        <button className="btn" onClick={() => run("high_temperature")}>High temperature</button>
        <button className="btn" onClick={() => run("over_capacity")}>Over capacity</button>
        <button className="btn" onClick={() => run("poor_air_quality")}>Poor air quality</button>
        <button className="btn" onClick={() => run("device_offline")}>Device offline</button>
        <button className="btn btn-ghost" onClick={() => run("device_online")}>Device back online</button>
      </div>
      {message && <div className="info-banner">{message}</div>}
      {error && <div className="error-box">{error}</div>}
    </Card>
  );
}

export default function Incidents() {
  const { user } = useAuth();
  const meta = useMeta();
  const [params] = useSearchParams();
  const highlight = params.get("highlight");
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const canAct = OPS.includes(user.role);
  const isStudent = user.role === "student";
  const rowRef = useRef(null);

  const alerts = useApi(() => api.alerts({ status, severity, limit: 200 }), [status, severity], { interval: 5000 });

  useEffect(() => {
    if (highlight && rowRef.current) rowRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [highlight, alerts.data]);

  const act = async (fn, id) => {
    setBusy(id); setError("");
    try { await fn(id); alerts.reload(); } catch (e) { setError(e.message); } finally { setBusy(null); }
  };

  return (
    <>
      <PageHeader
        title={isStudent ? "Emergency Alerts" : "Incidents & Alerts"}
        subtitle="Alerts come from simple threshold rules (not AI). This is a prototype monitoring system, not a certified fire-alarm or emergency system."
        actions={<LiveIndicator updatedAt={alerts.updatedAt} loading={alerts.loading} />}
      />
      {canAct && meta?.simulator_enabled && <DemoControls onDone={alerts.reload} />}

      {!isStudent && (
        <Card>
          <div className="filters">
            <label className="field"><span>Status</span>
              <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">All</option><option value="open">Open (active + acknowledged)</option><option value="active">Active</option><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option>
              </select></label>
            <label className="field"><span>Severity</span>
              <select className="select" value={severity} onChange={(e) => setSeverity(e.target.value)}>
                <option value="">All</option><option value="critical">Critical</option><option value="warning">Warning</option><option value="info">Info</option>
              </select></label>
          </div>
        </Card>
      )}

      {error && <div className="error-box">{error}</div>}
      <Card title={`${isStudent ? "Active alerts" : "Incident list"}`} padded={false}>
        <DataState result={alerts}>
          {(list) => list.length === 0 ? <EmptyState>{isStudent ? "No active emergency alerts." : "No incidents match these filters."}</EmptyState> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>#</th><th>Type / severity</th><th>Location</th><th>Time</th>{!isStudent && <th>Sensor / device</th>}<th>Status</th><th>Actions</th></tr></thead>
                <tbody>
                  {list.map((a) => (
                    <tr key={a.id} ref={String(a.id) === highlight ? rowRef : null} className={String(a.id) === highlight ? "row-highlight" : ""}>
                      <td>{a.id}</td>
                      <td>
                        <div className="strong">{ALERT_TYPE_LABELS[a.alert_type] || a.alert_type}</div>
                        <SeverityBadge severity={a.severity} />
                        <div className="small">{a.message}</div>
                      </td>
                      <td>{alertLocation(a)}</td>
                      <td>{fmtDateTime(a.created_at)}</td>
                      {!isStudent && (
                        <td>
                          <div>{a.device_uid || "-"}</div>
                          <div className="muted small">{a.sensor_type ? `${a.sensor_type}: ${fmtNum(a.value)} ${a.sensor_unit || ""}` : ""}</div>
                          <SimulatedTag simulated={!!a.is_simulated} />
                        </td>
                      )}
                      <td>
                        <AlertStatusBadge status={a.status} />
                        {a.acknowledged_by && <div className="muted small">Ack: {a.acknowledged_by}</div>}
                        {a.resolved_by && <div className="muted small">Resolved: {a.resolved_by}</div>}
                      </td>
                      <td>
                        <div className="row wrap">
                          <Link className="btn btn-sm" to={twinLink({ building_id: a.building_id, floor_id: a.floor_id, room_id: a.room_id, id: a.id })}>View on twin</Link>
                          {canAct && a.status === "active" && <button className="btn btn-sm" disabled={busy === a.id} onClick={() => act(api.acknowledge, a.id)}>Acknowledge</button>}
                          {canAct && a.status !== "resolved" && <button className="btn btn-sm btn-primary" disabled={busy === a.id} onClick={() => act(api.resolve, a.id)}>Resolve</button>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataState>
      </Card>
    </>
  );
}

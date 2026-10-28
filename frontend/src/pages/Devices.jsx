import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import { Card, DataState, EmptyState, LiveIndicator, PageHeader, SimulatedTag, StatusBadge } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { SENSOR_META } from "../utils/constants.js";
import { fmtDateTime, fmtNum, relativeTime, shortName } from "../utils/format.js";

function DeviceDetail({ id, onClose }) {
  const result = useApi(() => api.device(id), [id], { interval: 5000 });
  return (
    <Card title="Device details" actions={<button className="btn btn-sm btn-ghost" onClick={onClose}>Close</button>}>
      <DataState result={result}>
        {(d) => (
          <div className="stack">
            <div className="row wrap"><span className="strong">{d.device_uid}</span><StatusBadge status={d.status === "online" ? "normal" : "offline"} /><SimulatedTag simulated={!!d.is_simulated} /></div>
            <div className="metric-grid">
              <div className="metric"><div className="muted small">Location</div><div>{d.room_name}<div className="muted small">{shortName(d.building_name)} · {d.floor_name}</div></div></div>
              <div className="metric"><div className="muted small">Last seen</div><div>{d.last_seen ? fmtDateTime(d.last_seen) : "never"}<div className="muted small">{relativeTime(d.last_seen)}</div></div></div>
              <div className="metric"><div className="muted small">Readings stored</div><div className="metric-value">{d.readings_received}</div></div>
            </div>
            <table className="table">
              <thead><tr><th>Sensor</th><th>Latest reading</th><th>Updated</th></tr></thead>
              <tbody>{d.sensors.map((s) => <tr key={s.type}><td>{SENSOR_META[s.type]?.label || s.type}</td><td>{s.last_value === null ? "-" : `${fmtNum(s.last_value, s.type === "occupancy" ? 0 : 1)} ${s.unit || ""}`}</td><td>{relativeTime(s.last_recorded_at)}</td></tr>)}</tbody>
            </table>
            {d.recent_alerts.length > 0 && (
              <div><div className="strong">Recent alerts</div>{d.recent_alerts.map((a) => <div key={a.id} className="small">#{a.id} {a.message} <span className="muted">({a.status})</span></div>)}</div>
            )}
          </div>
        )}
      </DataState>
    </Card>
  );
}

export default function Devices() {
  const [params, setParams] = useSearchParams();
  const selected = params.get("device");
  const [status, setStatus] = useState("");
  const devices = useApi(() => api.devices({ status }), [status], { interval: 5000 });
  const open = (id) => setParams(id ? { device: id } : {});

  return (
    <>
      <PageHeader title="IoT Devices" subtitle="Device status is derived from the last message received. A device that sent no data is never shown as online." actions={<LiveIndicator updatedAt={devices.updatedAt} loading={devices.loading} />} />
      <Card>
        <div className="filters">
          <label className="field"><span>Status</span>
            <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All</option><option value="online">Online</option><option value="offline">Offline</option>
            </select></label>
        </div>
      </Card>
      <div className={selected ? "twin-layout" : ""}>
        <Card title="Devices" padded={false}>
          <DataState result={devices}>
            {(list) => list.length === 0 ? <EmptyState>No devices found.</EmptyState> : (
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>Device ID</th><th>Location</th><th>Sensors</th><th>Status</th><th>Last seen</th><th>Latest readings</th><th>Source</th></tr></thead>
                  <tbody>
                    {list.map((d) => (
                      <tr key={d.id} className={`clickable ${String(d.id) === selected ? "row-highlight" : ""}`} onClick={() => open(d.id)}>
                        <td className="strong">{d.device_uid}</td>
                        <td>{d.room_name}<div className="muted small">{shortName(d.building_name)}</div></td>
                        <td>{d.sensors.map((s) => SENSOR_META[s.type]?.label.split(" ")[0] || s.type).join(", ")}</td>
                        <td><StatusBadge status={d.status === "online" ? "normal" : "offline"} /></td>
                        <td>{relativeTime(d.last_seen)}</td>
                        <td className="small">{d.sensors.filter((s) => s.last_value !== null).slice(0, 4).map((s) => `${fmtNum(s.last_value, s.type === "occupancy" ? 0 : 1)}${s.unit && s.unit !== "people" ? s.unit : ""}`).join(" · ") || "-"}</td>
                        <td><SimulatedTag simulated={!!d.is_simulated} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </DataState>
        </Card>
        {selected && <DeviceDetail id={selected} onClose={() => open(null)} />}
      </div>
    </>
  );
}

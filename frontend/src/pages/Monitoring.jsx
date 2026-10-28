import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { TimeSeriesChart } from "../components/charts.jsx";
import { Card, DataState, EmptyState, LiveIndicator, PageHeader, RefreshButton, SimulatedTag } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { SENSOR_META } from "../utils/constants.js";
import { fmtNum, relativeTime, shortName, twinLink } from "../utils/format.js";

const RANGES = [{ v: 30, l: "30 min" }, { v: 60, l: "1 hour" }, { v: 180, l: "3 hours" }, { v: 360, l: "6 hours" }];

function SeriesCard({ type, filters, minutes }) {
  const meta = SENSOR_META[type];
  const result = useApi(() => api.series({ sensor_type: type, minutes, ...filters }), [type, minutes, JSON.stringify(filters)], { interval: 10000 });
  return (
    <Card title={`${meta.label} (${meta.unit})`} actions={result.data && type === "occupancy" ? <span className="muted small">sum of rooms</span> : <span className="muted small">average</span>}>
      <DataState result={result}>
        {(r) => <TimeSeriesChart points={r.points} dataKey={type === "occupancy" ? "sum" : "avg"} color={meta.color} unit={meta.unit} thresholds={r.thresholds} name={meta.label} height={200} />}
      </DataState>
    </Card>
  );
}

export default function Monitoring() {
  const [building, setBuilding] = useState("");
  const [floor, setFloor] = useState("");
  const [room, setRoom] = useState("");
  const [type, setType] = useState("");
  const [minutes, setMinutes] = useState(60);

  const buildings = useApi(() => api.buildings(), []);
  const detail = useApi(() => api.building(building), [building], { enabled: !!building });
  const rooms = useApi(() => api.rooms({ building_id: building, floor_id: floor }), [building, floor]);

  const filters = { building_id: building, floor_id: floor, room_id: room };
  const sensors = useApi(() => api.sensors({ ...filters, sensor_type: type }), [building, floor, room, type], { interval: 5000 });

  const pickBuilding = (v) => { setBuilding(v); setFloor(""); setRoom(""); };
  const pickFloor = (v) => { setFloor(v); setRoom(""); };
  const types = type ? [type] : Object.keys(SENSOR_META);

  return (
    <>
      <PageHeader title="Live Monitoring" subtitle="Latest sensor values and recent trends. Values are labelled SIMULATED unless they come from real hardware." actions={<><LiveIndicator updatedAt={sensors.updatedAt} loading={sensors.loading} /><RefreshButton onClick={sensors.reload} /></>} />

      <Card>
        <div className="filters">
          <label className="field"><span>Building</span>
            <select className="select" value={building} onChange={(e) => pickBuilding(e.target.value)}>
              <option value="">All buildings</option>
              {buildings.data?.map((b) => <option key={b.id} value={b.id}>{shortName(b.name)}</option>)}
            </select></label>
          <label className="field"><span>Floor</span>
            <select className="select" value={floor} onChange={(e) => pickFloor(e.target.value)} disabled={!building}>
              <option value="">All floors</option>
              {detail.data?.floors.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select></label>
          <label className="field"><span>Room</span>
            <select className="select" value={room} onChange={(e) => setRoom(e.target.value)}>
              <option value="">All rooms</option>
              {rooms.data?.filter((r) => r.has_sensors).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select></label>
          <label className="field"><span>Sensor</span>
            <select className="select" value={type} onChange={(e) => setType(e.target.value)}>
              <option value="">All sensors</option>
              {Object.entries(SENSOR_META).map(([k, m]) => <option key={k} value={k}>{m.label}</option>)}
            </select></label>
          <label className="field"><span>Chart period</span>
            <select className="select" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
              {RANGES.map((r) => <option key={r.v} value={r.v}>{r.l}</option>)}
            </select></label>
          <button className="btn btn-ghost" onClick={() => { pickBuilding(""); setType(""); }}>Clear filters</button>
        </div>
      </Card>

      <div className="grid grid-2">
        {types.map((t) => <SeriesCard key={t} type={t} filters={filters} minutes={minutes} />)}
      </div>

      <Card title="Current sensor readings" padded={false}>
        <DataState result={sensors}>
          {(list) => list.length === 0 ? <EmptyState>No sensors match these filters.</EmptyState> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Location</th><th>Sensor</th><th>Value</th><th>Device</th><th>Last update</th><th>Source</th></tr></thead>
                <tbody>
                  {list.map((s) => (
                    <tr key={s.id}>
                      <td><Link to={twinLink({ building_id: s.building_id, floor_id: s.floor_id, room_id: s.room_id })}>{s.room_name}</Link><div className="muted small">{shortName(s.building_name)} · {s.floor_name}</div></td>
                      <td>{SENSOR_META[s.type]?.label || s.type}{s.type === "occupancy" ? ` (${s.sensing_mode})` : ""}</td>
                      <td className="strong">{s.last_value === null ? "-" : fmtNum(s.last_value, s.type === "occupancy" ? 0 : 1)} {s.unit}</td>
                      <td>{s.device_uid} <span className={`pill ${s.device_online ? "ok" : "off"}`}>{s.device_online ? "online" : "offline"}</span></td>
                      <td>{relativeTime(s.last_recorded_at)}</td>
                      <td><SimulatedTag simulated={!!s.last_is_simulated} /></td>
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

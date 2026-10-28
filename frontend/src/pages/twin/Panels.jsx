import { Link } from "react-router-dom";
import { api } from "../../api/client.js";
import { AlertStatusBadge, Card, DataState, EmptyState, OccupancyBar, SeverityBadge, SimulatedTag, StatusBadge } from "../../components/ui.jsx";
import { TimeSeriesChart } from "../../components/charts.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { useApi } from "../../hooks/useApi.js";
import { ROOM_TYPE_LABELS, SENSOR_META, STAFF, STATUS_META } from "../../utils/constants.js";
import { fmtNum, relativeTime, shortName } from "../../utils/format.js";
import { layoutRooms } from "../../three/layout.js";

export function StatusLegend() {
  return (
    <div className="scene-legend">
      {Object.entries(STATUS_META).map(([key, m]) => (
        <span key={key}><span className="dot" style={{ background: m.scene }} /> {m.label}</span>
      ))}
    </div>
  );
}

/** Level 1: campus overview (list of buildings). */
export function CampusPanel({ buildings, onSelect }) {
  return (
    <Card title="Campus buildings" padded={false}>
      <div className="list">
        {buildings.map((b) => (
          <button key={b.id} className="list-item" onClick={() => onSelect(b)}>
            <div className="grow">
              <div className="strong">{shortName(b.name)}</div>
              <div className="muted small">
                {b.floors_count} floor{b.floors_count > 1 ? "s" : ""} · {b.rooms_count} rooms · {b.occupancy_pct === null ? "no occupancy data" : `${b.occupancy} people (${b.occupancy_pct}%)`}
              </div>
            </div>
            <StatusBadge status={b.status} />
          </button>
        ))}
      </div>
    </Card>
  );
}

/** Level 2: one building and its floors. */
export function BuildingPanel({ detail, onSelectFloor }) {
  return (
    <>
      <Card title={shortName(detail.name)} actions={<StatusBadge status={detail.status} />}>
        <p className="muted">{detail.description}</p>
        <div className="metric-grid">
          <Metric label="Floors" value={detail.floors_count} />
          <Metric label="Rooms" value={detail.rooms_count} />
          <Metric label="Occupancy" value={detail.occupancy_pct === null ? "-" : `${detail.occupancy} (${detail.occupancy_pct}%)`} />
          <Metric label="Devices online" value={`${detail.devices_online}/${detail.devices_total}`} />
          <Metric label="Active alerts" value={detail.active_alerts} tone={detail.active_alerts ? "bad" : ""} />
        </div>
      </Card>
      <Card title="Floors" padded={false}>
        <div className="list">
          {[...detail.floors].reverse().map((f) => (
            <button key={f.id} className="list-item" onClick={() => onSelectFloor(f)}>
              <div className="grow">
                <div className="strong">{f.name}</div>
                <div className="muted small">{f.rooms_count} rooms · {f.occupancy_pct === null ? "no occupancy data" : `${f.occupancy} people (${f.occupancy_pct}%)`}</div>
              </div>
              <StatusBadge status={f.status} />
            </button>
          ))}
        </div>
      </Card>
    </>
  );
}

/** Level 3: a schematic floor plan with selectable rooms. */
export function FloorPanel({ detail, floor, onSelectRoom }) {
  const slots = layoutRooms(floor.rooms.length, detail.width, detail.depth);
  const cols = slots[0]?.cols || 1;
  return (
    <Card title={`${floor.name} · ${shortName(detail.name)}`} actions={<StatusBadge status={floor.status} />}>
      <p className="muted small">Schematic layout (not to scale). Click a room for details.</p>
      <div className="floor-plan" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
        {floor.rooms.map((r) => {
          const m = STATUS_META[r.status] || STATUS_META.no_data;
          return (
            <button key={r.id} className="room-tile" style={{ borderColor: m.scene, background: m.bg }} onClick={() => onSelectRoom(r)}>
              <div className="strong">{r.name}</div>
              <div className="muted small">{ROOM_TYPE_LABELS[r.room_type] || r.room_type} · cap. {r.capacity}</div>
              <OccupancyBar value={r.occupancy} capacity={r.capacity} mode={r.occupancy_mode} />
              <div className="tile-foot small">
                <span>{r.has_sensors ? (r.in_class ? "Class in session" : "Free (timetable)") : "No sensors"}</span>
                <span style={{ color: m.color }}>{m.label}</span>
              </div>
            </button>
          );
        })}
      </div>
    </Card>
  );
}

function Metric({ label, value, unit, tone }) {
  return (
    <div className={`metric ${tone ? `tone-${tone}` : ""}`}>
      <div className="muted small">{label}</div>
      <div className="metric-value">{value}{unit ? <span className="metric-unit"> {unit}</span> : null}</div>
    </div>
  );
}

/** Level 4: room details with sensor values, class information and history. */
export function RoomPanel({ room }) {
  const { user } = useAuth();
  const canSeeHistory = STAFF.includes(user.role);
  const history = useApi(() => api.roomHistory(room.id, 120), [room.id], { interval: 15000, enabled: canSeeHistory && room.has_sensors });
  const occLabel = room.occupancy_mode === "presence" ? "Presence" : "Occupancy (estimated)";
  return (
    <>
      <Card title={room.name} actions={<StatusBadge status={room.status} />}>
        <div className="muted small">{shortName(room.building_name)} · {room.floor_name} · {ROOM_TYPE_LABELS[room.room_type] || room.room_type}</div>
        {room.has_sensors ? (
          <>
            <div className="metric-grid">
              <Metric label={occLabel} value={room.occupancy_mode === "presence" ? (room.occupancy ? "Detected" : "None") : `${room.occupancy ?? "-"} / ${room.capacity}`} />
              <Metric label="Temperature" value={fmtNum(room.temperature)} unit="°C" />
              <Metric label="Humidity" value={fmtNum(room.humidity)} unit="%" />
              <Metric label="Air quality" value={room.air_quality === null ? "n/a" : fmtNum(room.air_quality, 0)} unit={room.air_quality === null ? "" : "ppm"} />
            </div>
            <div className="row wrap small muted">
              <span>Last update: {relativeTime(room.last_update)}</span>
              <SimulatedTag simulated={room.data_simulated} />
            </div>
          </>
        ) : (
          <EmptyState>No sensors are installed in this room. Capacity: {room.capacity}.</EmptyState>
        )}
      </Card>

      <Card title="Classes (sample timetable)">
        <div className="two-col">
          <div>
            <div className="muted small">Current class</div>
            {room.current_class ? (
              <div><span className="strong">{room.current_class.course}</span><div className="muted small">{room.current_class.class_group} · {room.current_class.faculty} · {room.current_class.start_time}-{room.current_class.end_time}</div></div>
            ) : <div>None in session</div>}
          </div>
          <div>
            <div className="muted small">Next class</div>
            {room.next_class ? (
              <div><span className="strong">{room.next_class.course}</span><div className="muted small">{room.next_class.day_offset === 0 ? "Today" : room.next_class.day_name} {room.next_class.start_time}-{room.next_class.end_time} · {room.next_class.class_group}</div></div>
            ) : <div>None scheduled</div>}
          </div>
        </div>
      </Card>

      {room.alerts?.length > 0 && (
        <Card title="Open alerts">
          {room.alerts.map((a) => (
            <div key={a.id} className="alert-line">
              <SeverityBadge severity={a.severity} /> <AlertStatusBadge status={a.status} />
              <span>{a.message}</span>
            </div>
          ))}
        </Card>
      )}

      {room.sensors.length > 0 && (
        <Card title="Sensors" padded={false}>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Type</th><th>Value</th><th>Device</th><th>Updated</th></tr></thead>
              <tbody>
                {room.sensors.map((s) => (
                  <tr key={s.id}>
                    <td>{SENSOR_META[s.type]?.label || s.type}{s.type === "occupancy" ? ` (${s.sensing_mode})` : ""}</td>
                    <td>{s.last_value === null ? "-" : `${fmtNum(s.last_value, s.type === "occupancy" ? 0 : 1)} ${s.unit || ""}`}</td>
                    <td>{s.device_uid} <span className={`pill ${s.device_online ? "ok" : "off"}`}>{s.device_online ? "online" : "offline"}</span></td>
                    <td>{relativeTime(s.last_recorded_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {canSeeHistory && room.has_sensors && (
        <Card title="Last 2 hours">
          <DataState result={history}>
            {(h) => (
              <div className="stack">
                {["temperature", "humidity", "occupancy"].map((t) => (
                  <div key={t}>
                    <div className="muted small">{SENSOR_META[t].label} ({SENSOR_META[t].unit})</div>
                    <TimeSeriesChart points={h[t]} color={SENSOR_META[t].color} unit={SENSOR_META[t].unit} height={130} name={SENSOR_META[t].label} />
                  </div>
                ))}
              </div>
            )}
          </DataState>
        </Card>
      )}

      <div className="row">
        <Link className="btn btn-primary" to={`/navigation?destination=room:${room.id}`}>Navigate to this room</Link>
      </div>
    </>
  );
}

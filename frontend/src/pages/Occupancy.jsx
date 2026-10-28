import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { SimpleBarChart, TimeSeriesChart } from "../components/charts.jsx";
import { Card, DataState, LiveIndicator, OccupancyBar, PageHeader, StatCard } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { ROOM_TYPE_LABELS } from "../utils/constants.js";
import { shortName, twinLink } from "../utils/format.js";

export default function Occupancy() {
  const [buildingId, setBuildingId] = useState("");
  const summary = useApi(() => api.summary(), [], { interval: 8000 });
  const rooms = useApi(() => api.rooms({ building_id: buildingId }), [buildingId], { interval: 8000 });
  const trend = useApi(() => api.series({ sensor_type: "occupancy", minutes: 180, building_id: buildingId }), [buildingId], { interval: 30000 });
  const detail = useApi(() => api.building(buildingId), [buildingId], { enabled: !!buildingId, interval: 8000 });

  return (
    <>
      <PageHeader title="Occupancy" subtitle="Estimated occupancy from count-mode sensors. Presence-only sensors are shown as presence, never as a head count." actions={<LiveIndicator updatedAt={summary.updatedAt} loading={summary.loading} />} />
      <DataState result={summary}>
        {(s) => (
          <div className="stack">
            <div className="grid grid-4">
              <StatCard label="Campus occupancy" value={s.campus_occupancy_pct === null ? "-" : `${s.campus_occupancy_pct}%`} hint={`${s.campus_occupancy} of ${s.campus_capacity}`} />
              <StatCard label="Monitored rooms" value={s.monitored_rooms} hint={`of ${s.rooms_count}`} />
              <StatCard label="Teaching rooms in class" value={`${s.rooms_in_class_now}/${s.schedulable_rooms}`} hint="sample timetable" />
              <StatCard label="Last data" value={s.last_data_received ? new Date(s.last_data_received).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "-"} />
            </div>

            <div className="grid grid-2">
              <Card title="Building occupancy (%)">
                <SimpleBarChart data={s.buildings.map((b) => ({ label: shortName(b.name).split(" ")[0], value: b.occupancy_pct }))} unit="%" max={100} color="#6366f1" />
              </Card>
              <Card title="Occupancy trend – last 3 hours" actions={
                <select className="select select-sm" value={buildingId} onChange={(e) => setBuildingId(e.target.value)}>
                  <option value="">Whole campus</option>
                  {s.buildings.map((b) => <option key={b.id} value={b.id}>{shortName(b.name)}</option>)}
                </select>}>
                <DataState result={trend}>{(t) => <TimeSeriesChart points={t.points} dataKey="sum" color="#6366f1" unit="people" name="People (estimated)" />}</DataState>
              </Card>
            </div>

            {buildingId && (
              <Card title="Floor occupancy">
                <DataState result={detail}>
                  {(d) => (
                    <div className="grid grid-3">
                      {d.floors.map((f) => (
                        <div key={f.id} className="metric">
                          <div className="strong">{f.name}</div>
                          <div className="muted small">{f.occupancy_pct === null ? "no occupancy data" : `${f.occupancy} people · ${f.occupancy_pct}% of ${f.occupancy_capacity}`}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </DataState>
              </Card>
            )}

            <Card title="Room occupancy and capacity" padded={false}>
              <DataState result={rooms}>
                {(list) => (
                  <div className="table-wrap">
                    <table className="table">
                      <thead><tr><th>Room</th><th>Type</th><th>Capacity</th><th>Occupancy</th><th>Class now (sample)</th></tr></thead>
                      <tbody>
                        {[...list].sort((a, b) => (b.occupancy_pct ?? -1) - (a.occupancy_pct ?? -1)).map((r) => (
                          <tr key={r.id}>
                            <td><Link to={twinLink({ building_id: r.building_id, floor_id: r.floor_id, room_id: r.id })}>{r.name}</Link><div className="muted small">{shortName(r.building_name)} · {r.floor_name}</div></td>
                            <td>{ROOM_TYPE_LABELS[r.room_type] || r.room_type}</td>
                            <td>{r.capacity}</td>
                            <td style={{ minWidth: 160 }}><OccupancyBar value={r.occupancy} capacity={r.capacity} mode={r.occupancy_mode} /></td>
                            <td>{r.current_class ? r.current_class.course : "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </DataState>
            </Card>
          </div>
        )}
      </DataState>
    </>
  );
}

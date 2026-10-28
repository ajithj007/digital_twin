import { api } from "../../api/client.js";
import { Card, DataState, LiveIndicator, PageHeader, SimulatedTag, StatCard } from "../../components/ui.jsx";
import { TimeSeriesChart } from "../../components/charts.jsx";
import { useMeta } from "../../context/MetaContext.jsx";
import { useApi } from "../../hooks/useApi.js";
import { fmtNum, relativeTime } from "../../utils/format.js";
import { BuildingStatusList, IncidentList, TwinPreview } from "./shared.jsx";

export default function AdminDashboard() {
  const meta = useMeta();
  const summary = useApi(() => api.summary(), [], { interval: 5000 });
  const nav = useApi(() => api.navMap(), []);
  const trend = useApi(() => api.series({ sensor_type: "occupancy", minutes: 180 }), [], { interval: 30000 });
  return (
    <>
      <PageHeader title="Digital Operations Centre" subtitle="Administrator dashboard" actions={<LiveIndicator updatedAt={summary.updatedAt} loading={summary.loading} />} />
      <DataState result={summary}>
        {(s) => (
          <div className="stack">
            <div className="grid grid-6">
              <StatCard label="Campus occupancy" value={s.campus_occupancy_pct === null ? "-" : `${s.campus_occupancy_pct}%`} hint={`${s.campus_occupancy} of ${s.campus_capacity} (estimated)`} />
              <StatCard label="Buildings" value={s.buildings_count} hint={`${s.rooms_count} rooms · ${s.monitored_rooms} monitored`} />
              <StatCard label="Active alerts" value={s.alerts.active} tone={s.alerts.critical ? "bad" : s.alerts.active ? "warn" : "ok"} hint={`${s.alerts.critical} critical · ${s.alerts.warning} warning`} />
              <StatCard label="Active incidents" value={s.active_incidents} hint={`${s.acknowledged_incidents} acknowledged`} />
              <StatCard label="Sensor health" value={s.sensor_health_pct === null ? "-" : `${s.sensor_health_pct}%`} tone={s.devices_offline ? "warn" : "ok"} hint={`${s.devices_online}/${s.devices_total} devices online`} />
              <StatCard label="Room utilization now" value={s.room_utilization_pct === null ? "-" : `${s.room_utilization_pct}%`} hint={`${s.rooms_in_class_now}/${s.schedulable_rooms} teaching rooms in class (sample timetable)`} />
            </div>

            <div className="grid grid-2-1">
              <TwinPreview buildings={s.buildings} navMap={nav.data} />
              <BuildingStatusList buildings={s.buildings} />
            </div>

            <div className="grid grid-2">
              <Card title="Campus occupancy – last 3 hours">
                <DataState result={trend}>{(t) => <TimeSeriesChart points={t.points} dataKey="sum" color="#6366f1" unit="people" name="People (estimated)" height={220} />}</DataState>
                <p className="muted small">Sum of room occupancy estimates from count-mode sensors.</p>
              </Card>
              <IncidentList alerts={s.recent_alerts} canAct onChanged={summary.reload} />
            </div>

            <div className="grid grid-2">
              <Card title="Monitoring summary">
                <div className="metric-grid">
                  <div className="metric"><div className="muted small">Avg temperature</div><div className="metric-value">{fmtNum(s.avg_temperature)} °C</div></div>
                  <div className="metric"><div className="muted small">Avg humidity</div><div className="metric-value">{fmtNum(s.avg_humidity)} %</div></div>
                </div>
              </Card>
              <Card title="System health">
                <ul className="plain">
                  <li>Backend API: <strong>online</strong></li>
                  <li>Data source: <SimulatedTag simulated={meta?.data_source !== "hardware"} /> {meta?.data_source}</li>
                  <li>Last data received: {relativeTime(s.last_data_received)}</li>
                  <li>Simulator: {meta?.simulator_enabled ? "running" : "disabled"}</li>
                </ul>
              </Card>
            </div>
          </div>
        )}
      </DataState>
    </>
  );
}

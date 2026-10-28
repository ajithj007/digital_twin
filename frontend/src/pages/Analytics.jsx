import { useState } from "react";
import { api } from "../api/client.js";
import { MultiLineChart, SimpleBarChart, TimeSeriesChart } from "../components/charts.jsx";
import { Card, DataState, PageHeader, RefreshButton } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { ALERT_TYPE_LABELS } from "../utils/constants.js";
import { shortName } from "../utils/format.js";

export default function Analytics() {
  const [hours, setHours] = useState(6);
  const result = useApi(() => api.analytics(hours), [hours], { interval: 30000 });
  const series = (list) => list.map((b) => ({ name: shortName(b.building_name).split(" ")[0], points: b.points }));

  return (
    <>
      <PageHeader title="Analytics" subtitle="Trends from stored readings (SIMULATED unless hardware is connected)." actions={
        <>
          <select className="select select-sm" value={hours} onChange={(e) => setHours(Number(e.target.value))}>
            <option value={1}>Last 1 hour</option><option value={3}>Last 3 hours</option><option value={6}>Last 6 hours</option><option value={12}>Last 12 hours</option><option value={24}>Last 24 hours</option>
          </select>
          <RefreshButton onClick={result.reload} />
        </>} />
      <DataState result={result}>
        {(a) => (
          <div className="stack">
            <div className="grid grid-2">
              <Card title="Campus occupancy trend (estimated people)"><TimeSeriesChart points={a.occupancy_trend} dataKey="sum" color="#6366f1" unit="people" name="People" /></Card>
              <Card title="Building utilization now (% of monitored capacity)"><SimpleBarChart data={a.building_utilization.map((b) => ({ label: shortName(b.building_name).split(" ")[0], value: b.occupancy_pct }))} unit="%" max={100} color="#6366f1" /></Card>
            </div>
            <div className="grid grid-2">
              <Card title="Temperature by building (°C)"><MultiLineChart series={series(a.temperature_by_building)} unit="°C" /></Card>
              <Card title="Humidity by building (%)"><MultiLineChart series={series(a.humidity_by_building)} unit="%" /></Card>
            </div>
            <div className="grid grid-3">
              <Card title="Alerts by severity"><SimpleBarChart data={a.alerts_by_severity} color="#ea580c" height={200} /></Card>
              <Card title="Alerts by type"><SimpleBarChart data={a.alerts_by_type.map((x) => ({ label: (ALERT_TYPE_LABELS[x.label] || x.label).split(" ")[0], value: x.value }))} color="#dc2626" height={200} /></Card>
              <Card title="Alerts by status"><SimpleBarChart data={a.alerts_by_status} color="#0ea5e9" height={200} /></Card>
            </div>
            <div className="grid grid-2">
              <Card title="Room utilization – scheduled hours (top 10)">
                <SimpleBarChart horizontal height={320} unit="%" max={100} color="#2563eb" data={a.room_utilization.slice(0, 10).map((r) => ({ label: r.room_name, value: r.utilization_pct }))} />
                <p className="muted small">{a.room_utilization_note}</p>
              </Card>
              <Card title="Sensor availability (% devices online)">
                <SimpleBarChart height={320} unit="%" max={100} color="#16a34a" data={a.sensor_availability.map((b) => ({ label: shortName(b.building_name).split(" ")[0], value: b.availability_pct }))} />
              </Card>
            </div>
          </div>
        )}
      </DataState>
    </>
  );
}

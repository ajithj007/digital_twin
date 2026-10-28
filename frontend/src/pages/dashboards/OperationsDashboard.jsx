import { Link } from "react-router-dom";
import { api } from "../../api/client.js";
import { Card, DataState, EmptyState, LiveIndicator, PageHeader, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useApi } from "../../hooks/useApi.js";
import { relativeTime, shortName, twinLink } from "../../utils/format.js";
import { CampusStatusBanner, IncidentList, TwinPreview } from "./shared.jsx";

export default function OperationsDashboard() {
  const summary = useApi(() => api.summary(), [], { interval: 5000 });
  const open = useApi(() => api.alerts({ status: "open", limit: 8 }), [], { interval: 5000 });
  const offline = useApi(() => api.devices({ status: "offline" }), [], { interval: 10000 });
  const nav = useApi(() => api.navMap(), []);
  const reloadAll = () => { summary.reload(); open.reload(); };

  return (
    <>
      <PageHeader title="Operations Dashboard" subtitle="Current campus status, incidents and device health" actions={<LiveIndicator updatedAt={summary.updatedAt} loading={summary.loading} />} />
      <DataState result={summary}>
        {(s) => (
          <div className="stack">
            <CampusStatusBanner status={s.campus_status} active={s.active_incidents} />
            <div className="grid grid-5">
              <StatCard label="Active incidents" value={s.active_incidents} tone={s.active_incidents ? "warn" : "ok"} />
              <StatCard label="Critical alerts" value={s.alerts.critical} tone={s.alerts.critical ? "bad" : "ok"} />
              <StatCard label="Campus occupancy" value={s.campus_occupancy_pct === null ? "-" : `${s.campus_occupancy_pct}%`} hint={`${s.campus_occupancy} people (estimated)`} />
              <StatCard label="Sensor health" value={s.sensor_health_pct === null ? "-" : `${s.sensor_health_pct}%`} tone={s.devices_offline ? "warn" : "ok"} />
              <StatCard label="Devices offline" value={s.devices_offline} tone={s.devices_offline ? "warn" : "ok"} hint={`of ${s.devices_total}`} />
            </div>
            <div className="grid grid-2-1">
              <TwinPreview buildings={s.buildings} navMap={nav.data} />
              <Card title="Critical locations" padded={false}>
                {s.critical_locations.length === 0 && <EmptyState>No warning or critical locations.</EmptyState>}
                <div className="list">
                  {s.critical_locations.map((l) => (
                    <Link key={l.room_id} className="list-item" to={twinLink({ building_id: l.building_id, floor_id: l.floor_id, room_id: l.room_id })}>
                      <div className="grow"><div className="strong">{l.room_name}</div><div className="muted small">{shortName(l.building_name)}</div></div>
                      <StatusBadge status={l.status} />
                    </Link>
                  ))}
                </div>
              </Card>
            </div>
            <div className="grid grid-2">
              <DataState result={open}>{(alerts) => <IncidentList title="Active & acknowledged incidents" alerts={alerts} canAct onChanged={reloadAll} />}</DataState>
              <Card title="Device status – offline devices" padded={false}>
                <DataState result={offline}>
                  {(devices) => devices.length === 0 ? <EmptyState>All devices are online.</EmptyState> : (
                    <div className="list">
                      {devices.map((d) => (
                        <Link key={d.id} className="list-item" to={`/devices?device=${d.id}`}>
                          <div className="grow"><div className="strong">{d.device_uid}</div><div className="muted small">{d.room_name} · last seen {relativeTime(d.last_seen)}</div></div>
                          <StatusBadge status="offline" />
                        </Link>
                      ))}
                    </div>
                  )}
                </DataState>
              </Card>
            </div>
          </div>
        )}
      </DataState>
    </>
  );
}

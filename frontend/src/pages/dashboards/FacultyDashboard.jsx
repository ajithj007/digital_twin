import { Link } from "react-router-dom";
import { api } from "../../api/client.js";
import { Card, DataState, EmptyState, LiveIndicator, PageHeader, StatCard, StatusBadge } from "../../components/ui.jsx";
import { useApi } from "../../hooks/useApi.js";
import { shortName, twinLink } from "../../utils/format.js";
import { CampusStatusBanner, ClassTable, FreeRooms, IncidentList } from "./shared.jsx";

export default function FacultyDashboard() {
  const summary = useApi(() => api.summary(), [], { interval: 8000 });
  const me = useApi(() => api.dashboardMe(), [], { interval: 30000 });
  return (
    <>
      <PageHeader title="Faculty Dashboard" subtitle={me.data ? me.data.today : ""} actions={<LiveIndicator updatedAt={summary.updatedAt} loading={summary.loading} />} />
      <div className="stack">
        <DataState result={summary}>{(s) => <CampusStatusBanner status={s.campus_status} active={s.active_incidents} />}</DataState>
        <DataState result={me}>
          {(m) => (
            <>
              <div className="grid grid-4">
                <StatCard label="Today's classes" value={m.todays_classes.length} hint="from the sample timetable" />
                <StatCard label="Assigned rooms" value={m.assigned_rooms.length} />
                <StatCard label="Free rooms (next hour)" value={m.free_rooms_next_hour.length} hint="teaching rooms, sample timetable" />
                <StatCard label="Classes per week" value={m.weekly_class_count} />
              </div>
              <div className="grid grid-2">
                <Card title="Today's classes" padded={false}><ClassTable classes={m.todays_classes} /></Card>
                <Card title="Assigned rooms – status" padded={false}>
                  {m.assigned_rooms.length === 0 && <EmptyState>No rooms assigned.</EmptyState>}
                  <div className="list">
                    {m.assigned_rooms.map((r) => (
                      <Link key={r.room_id} className="list-item" to={twinLink({ building_id: r.building_id, floor_id: r.floor_id, room_id: r.room_id })}>
                        <div className="grow"><div className="strong">{r.room_name}</div><div className="muted small">{shortName(r.building_name)}{r.in_class ? " · class in session" : ""}</div></div>
                        <StatusBadge status={r.status} />
                      </Link>
                    ))}
                  </div>
                </Card>
              </div>
              <div className="grid grid-2">
                <Card title="Room availability – next hour" padded={false}>
                  <FreeRooms rooms={m.free_rooms_next_hour} />
                  <div className="card-body"><Link className="btn btn-sm" to="/rooms">Search rooms</Link></div>
                </Card>
                <DataState result={summary}>{(s) => <IncidentList title="Important alerts" alerts={s.recent_alerts.filter((a) => a.status !== "resolved")} canAct={false} />}</DataState>
              </div>
              <Card title="Quick navigation">
                <div className="row wrap">
                  <Link className="btn" to="/twin">Digital Twin</Link>
                  <Link className="btn" to="/navigation">Campus navigation</Link>
                  <Link className="btn" to="/rooms">Timetable & rooms</Link>
                  <Link className="btn" to="/monitoring">Live monitoring</Link>
                </div>
              </Card>
            </>
          )}
        </DataState>
      </div>
    </>
  );
}

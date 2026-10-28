import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../../api/client.js";
import CampusMap2D from "../../components/CampusMap2D.jsx";
import { Card, DataState, EmptyState, LiveIndicator, PageHeader } from "../../components/ui.jsx";
import { useApi } from "../../hooks/useApi.js";
import { CampusStatusBanner, ClassTable, FreeRooms, IncidentList } from "./shared.jsx";

function FindClassroom() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const navigate = useNavigate();
  useEffect(() => {
    if (q.trim().length < 2) { setResults([]); return undefined; }
    const t = setTimeout(() => api.search(q.trim()).then((r) => setResults(r.filter((x) => x.type === "room"))).catch(() => setResults([])), 250);
    return () => clearTimeout(t);
  }, [q]);
  return (
    <Card title="Find classroom">
      <input className="input" placeholder="Type a room name, e.g. Lab 204" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="list">
        {results.map((r) => (
          <div key={r.id} className="list-item static">
            <div className="grow"><div className="strong">{r.label}</div><div className="muted small">{r.sublabel}</div></div>
            <button className="btn btn-sm" onClick={() => navigate(`/navigation?destination=room:${r.id}`)}>Navigate</button>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function StudentDashboard() {
  const summary = useApi(() => api.summary(), [], { interval: 8000 });
  const me = useApi(() => api.dashboardMe(), [], { interval: 30000 });
  const nav = useApi(() => api.navMap(), []);
  const navigate = useNavigate();
  return (
    <>
      <PageHeader title="Student Dashboard" subtitle={me.data ? `${me.data.today} · ${me.data.class_group || ""}` : ""} actions={<LiveIndicator updatedAt={summary.updatedAt} loading={summary.loading} />} />
      <div className="stack">
        <DataState result={summary}>
          {(s) => (
            <>
              <CampusStatusBanner status={s.campus_status} active={s.active_incidents} />
              <div className="grid grid-2">
                <IncidentList title="Emergency alerts" alerts={s.recent_alerts} canAct={false} />
                <Card title="Campus map (sample layout)" actions={<Link className="btn btn-sm" to="/navigation">Navigation</Link>}>
                  <CampusMap2D buildings={s.buildings} navMap={nav.data} height={300} onSelectBuilding={(b) => navigate(`/twin?building=${b.id}`)} />
                </Card>
              </div>
            </>
          )}
        </DataState>
        <DataState result={me}>
          {(m) => (
            <div className="grid grid-2">
              <Card title="Today's timetable (sample data)" padded={false}><ClassTable classes={m.todays_classes} empty="No classes scheduled today." /></Card>
              <div className="stack">
                <FindClassroom />
                <Card title="Room availability – next hour" padded={false}><FreeRooms rooms={m.free_rooms_next_hour} /></Card>
              </div>
              <Card title="Announcements (sample)" padded={false}>
                {m.announcements.length === 0 && <EmptyState>No announcements.</EmptyState>}
                <div className="list">
                  {m.announcements.map((a) => <div key={a.id} className="list-item static"><div><div className="strong">{a.title}</div><div className="muted small">{a.body}</div></div></div>)}
                </div>
              </Card>
            </div>
          )}
        </DataState>
      </div>
    </>
  );
}

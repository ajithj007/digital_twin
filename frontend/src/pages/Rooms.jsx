import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { Card, DataState, EmptyState, ErrorBox, PageHeader, Tabs } from "../components/ui.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { ROOM_TYPE_LABELS } from "../utils/constants.js";
import { shortName, twinLink } from "../utils/format.js";

const todayStr = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
const nowHHMM = (plusHours = 0) => {
  const d = new Date(Date.now() + plusHours * 3600000);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};

function Availability() {
  const [form, setForm] = useState({ day: todayStr(), start: "10:00", end: "11:00", room_type: "", min_capacity: "" });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const search = async (e) => {
    e?.preventDefault();
    setBusy(true); setError(null);
    try { setResult(await api.availability({ ...form, min_capacity: form.min_capacity || 0 })); }
    catch (err) { setError(err); setResult(null); } finally { setBusy(false); }
  };

  return (
    <div className="stack">
      <Card title="Find an available room">
        <form className="filters" onSubmit={search}>
          <label className="field"><span>Date</span><input className="input" type="date" value={form.day} onChange={set("day")} required /></label>
          <label className="field"><span>From</span><input className="input" type="time" value={form.start} onChange={set("start")} required /></label>
          <label className="field"><span>To</span><input className="input" type="time" value={form.end} onChange={set("end")} required /></label>
          <label className="field"><span>Room type</span>
            <select className="select" value={form.room_type} onChange={set("room_type")}>
              <option value="">Any</option>
              {Object.entries(ROOM_TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select></label>
          <label className="field"><span>Min. capacity</span><input className="input" type="number" min="0" value={form.min_capacity} onChange={set("min_capacity")} placeholder="0" /></label>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Searching…" : "Search"}</button>
          <button type="button" className="btn btn-ghost" onClick={() => setForm({ ...form, day: todayStr(), start: nowHHMM(), end: nowHHMM(1) > nowHHMM() ? nowHHMM(1) : "23:59" })}>Now + 1 h</button>
        </form>
        {error && <ErrorBox error={error} />}
      </Card>

      {result && (
        <>
          <p className="muted small">{result.day_name} {result.day}, {result.start}-{result.end}. {result.note}</p>
          <Card title={`Available rooms (${result.available.length})`} padded={false}>
            {result.available.length === 0 && <EmptyState>No rooms are free in this period.</EmptyState>}
            <div className="list">
              {result.available.map((r) => (
                <div key={r.id} className="list-item static">
                  <div className="grow"><div className="strong">{r.name}</div><div className="muted small">{shortName(r.building_name)} · {r.floor_name} · {ROOM_TYPE_LABELS[r.room_type] || r.room_type} · capacity {r.capacity}</div></div>
                  <Link className="btn btn-sm" to={twinLink({ building_id: r.building_id, floor_id: r.floor_id, room_id: r.id })}>View on Digital Twin</Link>
                  <Link className="btn btn-sm" to={`/navigation?destination=room:${r.id}`}>Navigate</Link>
                </div>
              ))}
            </div>
          </Card>
          {result.busy.length > 0 && (
            <Card title={`Busy rooms (${result.busy.length})`} padded={false}>
              <div className="list">
                {result.busy.map((r) => (
                  <div key={r.id} className="list-item static">
                    <div className="grow"><div className="strong">{r.name}</div><div className="muted small">{shortName(r.building_name)} · {r.conflict.course} ({r.conflict.class_group}) {r.conflict.start_time}-{r.conflict.end_time}</div></div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function Timetable() {
  const { user } = useAuth();
  const initialMode = user.role === "student" ? "group" : user.role === "faculty" ? "faculty" : "room";
  const [mode, setMode] = useState(initialMode);
  const groups = useApi(() => api.timetableGroups(), []);
  const rooms = useApi(() => api.rooms({}), []);
  const [value, setValue] = useState(user.role === "student" ? user.class_group || "" : user.role === "faculty" ? user.name : "");

  const params = mode === "room" ? { room_id: value } : mode === "group" ? { class_group: value } : { faculty: value };
  const table = useApi(() => api.timetable(params), [mode, value], { enabled: !!value });

  const options = mode === "room" ? (rooms.data || []).filter((r) => ["classroom", "lab", "seminar"].includes(r.room_type)).map((r) => ({ v: r.id, l: `${r.name} (${shortName(r.building_name)})` }))
    : mode === "group" ? (groups.data?.class_groups || []).map((g) => ({ v: g, l: g }))
      : (groups.data?.faculty || []).map((f) => ({ v: f, l: f }));

  return (
    <div className="stack">
      <Card>
        <div className="filters">
          <label className="field"><span>View timetable by</span>
            <select className="select" value={mode} onChange={(e) => { setMode(e.target.value); setValue(""); }}>
              <option value="room">Room</option><option value="group">Class group</option><option value="faculty">Faculty</option>
            </select></label>
          <label className="field"><span>{mode === "room" ? "Room" : mode === "group" ? "Class group" : "Faculty"}</span>
            <select className="select" value={value} onChange={(e) => setValue(e.target.value)}>
              <option value="">Select…</option>
              {options.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
            </select></label>
        </div>
      </Card>
      {!value && <EmptyState>Select an item to see its weekly timetable.</EmptyState>}
      {value && (
        <DataState result={table}>
          {(t) => (
            <div className="week-grid">
              {t.day_names.slice(0, 6).map((day, i) => {
                const entries = t.entries.filter((e) => e.day_of_week === i);
                return (
                  <Card key={day} title={day} padded={false}>
                    {entries.length === 0 && <EmptyState>No classes</EmptyState>}
                    {entries.map((e) => (
                      <div key={e.id} className="slot">
                        <div className="strong">{e.start_time}-{e.end_time}</div>
                        <div>{e.course}</div>
                        <div className="muted small">{mode !== "room" ? e.room_name : e.class_group} · {mode !== "faculty" ? e.faculty : e.class_group}</div>
                      </div>
                    ))}
                  </Card>
                );
              })}
            </div>
          )}
        </DataState>
      )}
      <p className="muted small">Timetable data is SAMPLE data created for the prototype. It is not connected to ASIET's official timetable system.</p>
    </div>
  );
}

export default function Rooms() {
  const [tab, setTab] = useState("availability");
  return (
    <>
      <PageHeader title="Rooms & Timetable" subtitle="Room availability and timetable (sample data)" />
      <Tabs value={tab} onChange={setTab} tabs={[{ value: "availability", label: "Room availability" }, { value: "timetable", label: "Timetable" }]} />
      {tab === "availability" ? <Availability /> : <Timetable />}
    </>
  );
}

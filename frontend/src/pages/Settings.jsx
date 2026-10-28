import { useState } from "react";
import { api } from "../api/client.js";
import { Badge, Card, DataState, PageHeader, SimulatedTag, Tabs } from "../components/ui.jsx";
import { useMeta } from "../context/MetaContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { ROLE_LABELS, SENSOR_META } from "../utils/constants.js";
import { fmtDateTime } from "../utils/format.js";

function RuleRow({ rule, onSaved }) {
  const [threshold, setThreshold] = useState(rule.threshold);
  const [severity, setSeverity] = useState(rule.severity);
  const [enabled, setEnabled] = useState(!!rule.enabled);
  const [state, setState] = useState("");
  const dirty = Number(threshold) !== rule.threshold || severity !== rule.severity || enabled !== !!rule.enabled;

  const unit = rule.rule_type === "device_offline" ? "seconds without data" : rule.rule_type === "over_capacity" ? "% above capacity" : SENSOR_META[rule.sensor_type]?.unit || "";
  const save = async () => {
    setState("saving");
    try {
      await api.updateRule(rule.id, { threshold: Number(threshold), severity, enabled });
      setState("saved");
      onSaved();
    } catch (e) { setState(e.message); }
  };
  return (
    <tr>
      <td><div className="strong">{rule.name}</div><div className="muted small">{rule.description}</div></td>
      <td>{rule.rule_type === "threshold" ? `${SENSOR_META[rule.sensor_type]?.label || rule.sensor_type} ${rule.operator}` : rule.rule_type === "over_capacity" ? "Occupancy over capacity +" : "No data for"}</td>
      <td><input className="input input-sm" type="number" step="any" value={threshold} onChange={(e) => setThreshold(e.target.value)} /> <span className="muted small">{unit}</span></td>
      <td>
        <select className="select select-sm" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="info">Info</option><option value="warning">Warning</option><option value="critical">Critical</option>
        </select>
      </td>
      <td><input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} aria-label="Enabled" /></td>
      <td>
        <button className="btn btn-sm btn-primary" disabled={!dirty || state === "saving"} onClick={save}>Save</button>
        {state && state !== "saving" && <div className="small muted">{state === "saved" ? "Saved" : state}</div>}
      </td>
    </tr>
  );
}

function Rules() {
  const rules = useApi(() => api.rules(), []);
  return (
    <Card title="Alert rules (configurable thresholds)" padded={false}>
      <p className="muted small card-body">Simple conditional rules, not AI. Default values are SAMPLE thresholds: set them according to the sensor datasheets and college policy.</p>
      <DataState result={rules}>
        {(list) => (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Rule</th><th>Condition</th><th>Threshold</th><th>Severity</th><th>On</th><th></th></tr></thead>
              <tbody>{list.map((r) => <RuleRow key={`${r.id}-${r.threshold}-${r.severity}-${r.enabled}`} rule={r} onSaved={rules.reload} />)}</tbody>
            </table>
          </div>
        )}
      </DataState>
    </Card>
  );
}

function Users() {
  const users = useApi(() => api.users(), []);
  return (
    <Card title="Users and roles" padded={false}>
      <DataState result={users}>
        {(list) => (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Class group</th></tr></thead>
              <tbody>{list.map((u) => <tr key={u.id}><td>{u.name}</td><td>{u.email}</td><td><Badge>{ROLE_LABELS[u.role]}</Badge></td><td>{u.class_group || "-"}</td></tr>)}</tbody>
            </table>
          </div>
        )}
      </DataState>
      <p className="muted small card-body">These are DEMO accounts created in the sample database. User creation/editing is not implemented yet.</p>
    </Card>
  );
}

function Audit() {
  const audit = useApi(() => api.audit(), [], { interval: 10000 });
  return (
    <Card title="Audit log (latest 100)" padded={false}>
      <DataState result={audit}>
        {(list) => (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Detail</th></tr></thead>
              <tbody>{list.map((l) => <tr key={l.id}><td>{fmtDateTime(l.ts)}</td><td>{l.actor}</td><td>{l.action}</td><td className="small">{l.detail}</td></tr>)}</tbody>
            </table>
          </div>
        )}
      </DataState>
    </Card>
  );
}

function System() {
  const meta = useMeta();
  return (
    <Card title="System information">
      {!meta ? <p className="muted">Loading…</p> : (
        <ul className="plain">
          <li>Data source: <SimulatedTag simulated={meta.data_source !== "hardware"} /> <strong>{meta.data_source}</strong> ({meta.simulated_devices} simulated, {meta.hardware_devices} hardware devices)</li>
          <li>Simulator: {meta.simulator_enabled ? "running" : "disabled"}</li>
          <li>Campus layout: {meta.campus_data_is_sample ? "SAMPLE data (replace backend/app/campus_data.py)" : "custom"}</li>
          <li>Timetable: {meta.timetable_is_sample ? "SAMPLE data" : "custom"}</li>
        </ul>
      )}
      <h4>Connecting a real ESP32</h4>
      <ol className="steps small">
        <li>Register the device (POST <code>/api/devices</code>, administrator token) with its room and sensors.</li>
        <li>The ESP32 sends <code>POST /api/ingest</code> with header <code>X-Device-Key</code> and JSON like <code>{`{"device_uid":"ESP32-A1B2C3","readings":[{"sensor_type":"temperature","value":28.4}]}`}</code>.</li>
        <li>Set <code>SIMULATOR_ENABLED=0</code> when only real data should be shown.</li>
      </ol>
      <p className="muted small">See docs/ESP32_INTEGRATION.md for a complete example.</p>
    </Card>
  );
}

export default function Settings() {
  const [tab, setTab] = useState("rules");
  return (
    <>
      <PageHeader title="Settings" subtitle="Administrator tools" />
      <Tabs value={tab} onChange={setTab} tabs={[{ value: "rules", label: "Alert rules" }, { value: "users", label: "Users & roles" }, { value: "audit", label: "Audit log" }, { value: "system", label: "System" }]} />
      {tab === "rules" && <Rules />}
      {tab === "users" && <Users />}
      {tab === "audit" && <Audit />}
      {tab === "system" && <System />}
    </>
  );
}

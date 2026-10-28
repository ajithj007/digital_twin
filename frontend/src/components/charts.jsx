import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtTime } from "../utils/format.js";

const AXIS = { fontSize: 11, fill: "#64748b" };
const PALETTE = ["#2563eb", "#ef4444", "#16a34a", "#f59e0b", "#7c3aed", "#0891b2", "#db2777"];

function toData(points, key) {
  return (points || []).map((p) => ({ time: fmtTime(p.t), value: p[key] }));
}

/** One line (e.g. average temperature) with optional threshold lines. */
export function TimeSeriesChart({ points, dataKey = "avg", color = "#2563eb", unit = "", thresholds = [], height = 220, name = "Value" }) {
  const data = toData(points, dataKey);
  if (!data.length) return <div className="empty">No readings in this period yet.</div>;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="time" tick={AXIS} minTickGap={32} />
        <YAxis tick={AXIS} domain={["auto", "auto"]} unit={unit && unit.length <= 3 ? unit : ""} width={56} />
        <Tooltip formatter={(v) => [`${v}${unit ? ` ${unit}` : ""}`, name]} />
        {thresholds.map((t, i) => (
          <ReferenceLine key={i} y={t.value} stroke={t.severity === "critical" ? "#dc2626" : "#f59e0b"} strokeDasharray="5 4"
            label={{ value: `${t.severity} ${t.operator}${t.value}`, fontSize: 10, fill: "#64748b", position: "insideTopRight" }} />
        ))}
        <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Several lines on one chart: series = [{ name, points }] */
export function MultiLineChart({ series, dataKey = "avg", unit = "", height = 260 }) {
  const times = new Map();
  series.forEach((s, i) => s.points.forEach((p) => {
    const row = times.get(p.t) || { t: p.t, time: fmtTime(p.t) };
    row[`s${i}`] = p[dataKey];
    times.set(p.t, row);
  }));
  const data = [...times.values()].sort((a, b) => a.t.localeCompare(b.t));
  if (!data.length) return <div className="empty">No readings in this period yet.</div>;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="time" tick={AXIS} minTickGap={32} />
        <YAxis tick={AXIS} domain={["auto", "auto"]} width={56} />
        <Tooltip formatter={(v) => `${v}${unit ? ` ${unit}` : ""}`} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {series.map((s, i) => (
          <Line key={s.name} type="monotone" name={s.name} dataKey={`s${i}`} stroke={PALETTE[i % PALETTE.length]} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Simple bar chart: data = [{ label, value }] */
export function SimpleBarChart({ data, color = "#2563eb", unit = "", height = 240, horizontal = false, max }) {
  const rows = (data || []).filter((d) => d.value !== null && d.value !== undefined);
  if (!rows.length) return <div className="empty">No data.</div>;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout={horizontal ? "vertical" : "horizontal"} margin={{ top: 8, right: 16, left: horizontal ? 40 : -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        {horizontal ? (
          <>
            <XAxis type="number" tick={AXIS} domain={[0, max || "auto"]} />
            <YAxis type="category" dataKey="label" tick={AXIS} width={120} />
          </>
        ) : (
          <>
            <XAxis dataKey="label" tick={AXIS} interval={0} />
            <YAxis tick={AXIS} domain={[0, max || "auto"]} width={48} />
          </>
        )}
        <Tooltip formatter={(v) => `${v}${unit}`} />
        <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

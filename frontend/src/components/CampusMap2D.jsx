import { STATUS_META } from "../utils/constants.js";
import { shortName } from "../utils/format.js";

/** Top-down SVG campus map (sample layout). Shows roads, buildings with status colours and an optional route. */
export default function CampusMap2D({ buildings = [], navMap, route = null, onSelectBuilding, highlightBuildingId, height = 420 }) {
  const nodes = Object.fromEntries((navMap?.nodes || []).map((n) => [n.key, n]));
  const pad = 12;
  const minX = -125, maxX = 125, minZ = -108, maxZ = 138;
  const viewBox = `${minX - pad} ${minZ - pad} ${maxX - minX + 2 * pad} ${maxZ - minZ + 2 * pad}`;
  const dest = route && route.length ? route[route.length - 1] : null;
  const start = route && route.length ? route[0] : null;

  return (
    <svg viewBox={viewBox} style={{ width: "100%", height }} className="map2d" role="img" aria-label="Campus map (sample layout)">
      <rect x={minX - pad} y={minZ - pad} width={maxX - minX + 2 * pad} height={maxZ - minZ + 2 * pad} fill="#eef2f8" />
      {(navMap?.edges || []).map((e, i) =>
        nodes[e.a] && nodes[e.b] ? (
          <line key={i} x1={nodes[e.a].x} y1={nodes[e.a].z} x2={nodes[e.b].x} y2={nodes[e.b].z}
            stroke={e.kind === "road" ? "#b3bfd0" : "#cbd5e1"} strokeWidth={e.kind === "road" ? 5 : 2.4} strokeLinecap="round" />
        ) : null
      )}
      <rect x={28} y={86} width={40} height={28} fill="#d8dfea" stroke="#b3bfd0" />
      <text x={48} y={102} textAnchor="middle" fontSize="5" fill="#64748b">Parking</text>
      {buildings.map((b) => {
        const color = (STATUS_META[b.status] || STATUS_META.no_data).scene;
        const hl = b.id === highlightBuildingId;
        return (
          <g key={b.id} onClick={() => onSelectBuilding?.(b)} style={{ cursor: onSelectBuilding ? "pointer" : "default" }}>
            <rect x={b.x - b.width / 2} y={b.z - b.depth / 2} width={b.width} height={b.depth} rx="2"
              fill="#dbe4f1" stroke={hl ? "#dc2626" : "#64748b"} strokeWidth={hl ? 2.5 : 1} />
            <rect x={b.x - b.width / 2} y={b.z - b.depth / 2} width={b.width} height="3.5" rx="1.5" fill={color} />
            <text x={b.x} y={b.z + 2} textAnchor="middle" fontSize="5.2" fill="#1e293b">{shortName(b.name)}</text>
          </g>
        );
      })}
      {nodes.main_gate && (
        <g>
          <rect x={-6} y={122} width={12} height={5} fill="#1d4ed8" />
          <text x={0} y={134} textAnchor="middle" fontSize="5" fill="#334155">Main Gate</text>
        </g>
      )}
      {route && route.length > 1 && (
        <polyline points={route.map((p) => `${p.x},${p.z}`).join(" ")} fill="none" stroke="#2563eb" strokeWidth="2.6" strokeLinejoin="round" strokeLinecap="round" strokeDasharray="5 3" />
      )}
      {start && <circle cx={start.x} cy={start.z} r="3.6" fill="#16a34a" stroke="#fff" strokeWidth="1" />}
      {dest && <circle cx={dest.x} cy={dest.z} r="4.2" fill="#dc2626" stroke="#fff" strokeWidth="1.2" />}
    </svg>
  );
}

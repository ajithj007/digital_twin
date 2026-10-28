export function relativeTime(iso) {
  if (!iso) return "never";
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

export const fmtTime = (iso) =>
  iso ? new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "-";

export const fmtDateTime = (iso) =>
  iso
    ? new Date(iso).toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
    : "-";

export const fmtNum = (value, digits = 1) =>
  value === null || value === undefined ? "-" : Number(value).toFixed(digits).replace(/\.0+$/, "");

export const shortName = (name) => (name || "").replace(" (sample)", "");

export function twinLink({ building_id, floor_id, room_id, id } = {}) {
  const p = new URLSearchParams();
  if (building_id) p.set("building", building_id);
  if (floor_id) p.set("floor", floor_id);
  if (room_id) p.set("room", room_id);
  if (id) p.set("alert", id);
  return `/twin?${p.toString()}`;
}

export const alertLocation = (a) =>
  [a.room_name, a.floor_name, a.building_name && shortName(a.building_name)].filter(Boolean).join(" · ");

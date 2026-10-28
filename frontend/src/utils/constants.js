export const ALL_ROLES = ["admin", "faculty", "student", "operations"];
export const STAFF = ["admin", "faculty", "operations"];
export const OPS = ["admin", "operations"];

export const ROLE_LABELS = {
  admin: "Administrator",
  faculty: "Faculty",
  student: "Student",
  operations: "Operations / Security",
};

export const STATUS_META = {
  normal: { label: "Normal", color: "#16a34a", bg: "#dcfce7", scene: "#4ade80" },
  attention: { label: "Attention", color: "#a16207", bg: "#fef9c3", scene: "#facc15" },
  warning: { label: "Warning", color: "#c2410c", bg: "#ffedd5", scene: "#fb923c" },
  critical: { label: "Critical", color: "#b91c1c", bg: "#fee2e2", scene: "#ef4444" },
  offline: { label: "Offline", color: "#4b5563", bg: "#e5e7eb", scene: "#9ca3af" },
  no_data: { label: "Not monitored", color: "#64748b", bg: "#f1f5f9", scene: "#cbd5e1" },
};

export const SEVERITY_META = {
  info: { label: "Info", color: "#1d4ed8", bg: "#dbeafe" },
  warning: { label: "Warning", color: "#c2410c", bg: "#ffedd5" },
  critical: { label: "Critical", color: "#b91c1c", bg: "#fee2e2" },
};

export const ALERT_STATUS_META = {
  active: { label: "Active", color: "#b91c1c", bg: "#fee2e2" },
  acknowledged: { label: "Acknowledged", color: "#a16207", bg: "#fef9c3" },
  resolved: { label: "Resolved", color: "#15803d", bg: "#dcfce7" },
};

export const SENSOR_META = {
  temperature: { label: "Temperature", unit: "°C", color: "#ef4444" },
  humidity: { label: "Humidity", unit: "%", color: "#0ea5e9" },
  occupancy: { label: "Occupancy", unit: "people", color: "#6366f1" },
  air_quality: { label: "Air quality (CO₂ eq.)", unit: "ppm", color: "#14b8a6" },
};

export const ALERT_TYPE_LABELS = {
  high_temperature: "High temperature",
  high_humidity: "High humidity",
  poor_air_quality: "Poor air quality",
  over_capacity: "Over capacity",
  device_offline: "Device offline",
};

export const ROOM_TYPE_LABELS = {
  classroom: "Classroom",
  lab: "Laboratory",
  seminar: "Seminar hall",
  library: "Library",
  auditorium: "Auditorium",
  canteen: "Canteen",
  office: "Office",
};

// Sidebar. `labels` overrides the label for a role.
export const NAV_ITEMS = [
  { path: "/", label: "Dashboard", icon: "grid", roles: ALL_ROLES, end: true },
  { path: "/twin", label: "Digital Twin", icon: "cube", roles: ALL_ROLES },
  { path: "/monitoring", label: "Live Monitoring", icon: "activity", roles: STAFF },
  { path: "/occupancy", label: "Occupancy", icon: "users", roles: STAFF },
  { path: "/incidents", label: "Incidents & Alerts", icon: "alert", roles: ALL_ROLES, labels: { student: "Emergency Alerts", faculty: "Alerts" } },
  { path: "/navigation", label: "Navigation", icon: "compass", roles: ALL_ROLES, labels: { student: "Navigation & Map" } },
  { path: "/rooms", label: "Rooms & Timetable", icon: "calendar", roles: ALL_ROLES },
  { path: "/devices", label: "IoT Devices", icon: "chip", roles: OPS },
  { path: "/analytics", label: "Analytics", icon: "chart", roles: STAFF },
  { path: "/settings", label: "Settings", icon: "settings", roles: ["admin"] },
];

export const DEMO_ACCOUNTS = [
  { role: "admin", email: "admin@asiet.demo", password: "Admin@123" },
  { role: "faculty", email: "faculty@asiet.demo", password: "Faculty@123" },
  { role: "student", email: "student@asiet.demo", password: "Student@123" },
  { role: "operations", email: "security@asiet.demo", password: "Security@123" },
];

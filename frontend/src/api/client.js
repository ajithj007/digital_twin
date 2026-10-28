// All backend calls go through this file, so URLs and error handling live in one place.
const BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
const TOKEN_KEY = "asiet_token";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

function errorMessage(body, status) {
  if (body && body.detail) {
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((d) => d.msg).join("; ");
    if (body.detail.message) return body.detail.message;
  }
  return `Request failed (${status})`;
}

async function request(path, { method = "GET", body, params } = {}) {
  const query = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") query.append(k, v);
  });
  const url = `${BASE}${path}${query.toString() ? `?${query}` : ""}`;
  const headers = { Accept: "application/json" };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch {
    throw new ApiError("Cannot reach the backend. Is the FastAPI server running on port 8000?", 0);
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    /* empty body */
  }
  if (!response.ok) {
    if (response.status === 401 && token) window.dispatchEvent(new Event("asiet-unauthorized"));
    throw new ApiError(errorMessage(data, response.status), response.status);
  }
  return data;
}

export const api = {
  // auth + meta
  login: (email, password) => request("/auth/login", { method: "POST", body: { email, password } }),
  me: () => request("/auth/me"),
  meta: () => request("/meta"),
  // campus
  buildings: () => request("/buildings"),
  building: (id) => request(`/buildings/${id}`),
  rooms: (params) => request("/rooms", { params }),
  room: (id) => request(`/rooms/${id}`),
  roomHistory: (id, minutes = 120) => request(`/rooms/${id}/history`, { params: { minutes } }),
  // monitoring
  sensors: (params) => request("/sensors", { params }),
  series: (params) => request("/monitoring/series", { params }),
  // dashboards
  summary: () => request("/dashboard/summary"),
  dashboardMe: () => request("/dashboard/me"),
  analytics: (hours = 6) => request("/analytics/overview", { params: { hours } }),
  search: (q) => request("/search", { params: { q } }),
  // alerts
  alerts: (params) => request("/alerts", { params }),
  acknowledge: (id) => request(`/alerts/${id}/acknowledge`, { method: "POST" }),
  resolve: (id) => request(`/alerts/${id}/resolve`, { method: "POST" }),
  // devices
  devices: (params) => request("/devices", { params }),
  device: (id) => request(`/devices/${id}`),
  // rules, simulator, admin
  rules: () => request("/rules"),
  updateRule: (id, body) => request(`/rules/${id}`, { method: "PUT", body }),
  inject: (kind, room_id) => request("/simulator/inject", { method: "POST", body: { kind, room_id } }),
  users: () => request("/admin/users"),
  audit: () => request("/admin/audit"),
  // navigation + timetable
  navMap: () => request("/navigation/map"),
  navLocations: () => request("/navigation/locations"),
  route: (source, destination) => request("/navigation/route", { params: { source, destination } }),
  timetable: (params) => request("/timetable", { params }),
  timetableGroups: () => request("/timetable/groups"),
  availability: (params) => request("/timetable/availability", { params }),
};

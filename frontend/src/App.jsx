import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { ProtectedRoute, RoleRoute } from "./components/RouteGuards.jsx";
import { ALL_ROLES, OPS, STAFF } from "./utils/constants.js";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import DigitalTwin from "./pages/DigitalTwin.jsx";
import Monitoring from "./pages/Monitoring.jsx";
import Occupancy from "./pages/Occupancy.jsx";
import Incidents from "./pages/Incidents.jsx";
import Navigation from "./pages/Navigation.jsx";
import Rooms from "./pages/Rooms.jsx";
import Devices from "./pages/Devices.jsx";
import Analytics from "./pages/Analytics.jsx";
import Settings from "./pages/Settings.jsx";

const guard = (roles, element) => <RoleRoute roles={roles}>{element}</RoleRoute>;

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/twin" element={guard(ALL_ROLES, <DigitalTwin />)} />
        <Route path="/monitoring" element={guard(STAFF, <Monitoring />)} />
        <Route path="/occupancy" element={guard(STAFF, <Occupancy />)} />
        <Route path="/incidents" element={guard(ALL_ROLES, <Incidents />)} />
        <Route path="/navigation" element={guard(ALL_ROLES, <Navigation />)} />
        <Route path="/rooms" element={guard(ALL_ROLES, <Rooms />)} />
        <Route path="/devices" element={guard(OPS, <Devices />)} />
        <Route path="/analytics" element={guard(STAFF, <Analytics />)} />
        <Route path="/settings" element={guard(["admin"], <Settings />)} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

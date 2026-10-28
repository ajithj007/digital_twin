import { useAuth } from "../context/AuthContext.jsx";
import AdminDashboard from "./dashboards/AdminDashboard.jsx";
import FacultyDashboard from "./dashboards/FacultyDashboard.jsx";
import OperationsDashboard from "./dashboards/OperationsDashboard.jsx";
import StudentDashboard from "./dashboards/StudentDashboard.jsx";

/** Each role gets its own dashboard. */
export default function Dashboard() {
  const { user } = useAuth();
  if (user.role === "admin") return <AdminDashboard />;
  if (user.role === "operations") return <OperationsDashboard />;
  if (user.role === "faculty") return <FacultyDashboard />;
  return <StudentDashboard />;
}

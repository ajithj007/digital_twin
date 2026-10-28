import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { Loading } from "./ui.jsx";

/** Only logged-in users may see the app. Otherwise go to /login. */
export function ProtectedRoute({ children }) {
  const { user, checking } = useAuth();
  const location = useLocation();
  if (checking) return <Loading text="Restoring session…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return children;
}

/** Page-level role check (the backend enforces the same rules on its API). */
export function RoleRoute({ roles, children }) {
  const { user } = useAuth();
  if (!roles.includes(user.role)) {
    return (
      <div className="card"><div className="card-body">
        <h2>Access restricted</h2>
        <p className="muted">Your role does not have access to this module.</p>
      </div></div>
    );
  }
  return children;
}

import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/client.js";
import Logo from "../components/Logo.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { DEMO_ACCOUNTS, ROLE_LABELS } from "../utils/constants.js";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const meta = useApi(() => api.meta(), []);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email.trim(), password);
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-head">
          <Logo size={56} />
          <div>
            <h1>ASIET Campus Digital Twin</h1>
            <p className="muted">Adi Shankara Institute of Engineering and Technology, Kalady</p>
          </div>
        </div>

        <form onSubmit={submit} className="login-form">
          <label className="field">
            <span>Email</span>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@asiet.demo" autoComplete="username" required />
          </label>
          <label className="field">
            <span>Password</span>
            <div className="password-row">
              <input className="input" type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShow((s) => !s)}>{show ? "Hide" : "Show"}</button>
            </div>
          </label>
          {error && <div className="error-box" role="alert">{error}</div>}
          <button className="btn btn-primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        </form>

        <div className="demo-box">
          <div className="demo-title">Demo accounts (prototype only)</div>
          <p className="muted small">Sign-in is checked by the backend API. These accounts are created in the sample database.</p>
          <div className="demo-grid">
            {DEMO_ACCOUNTS.map((a) => (
              <button key={a.role} type="button" className="btn btn-sm" onClick={() => { setEmail(a.email); setPassword(a.password); }}>
                {ROLE_LABELS[a.role]}
              </button>
            ))}
          </div>
          {meta.error && <p className="muted small">Backend status: {meta.error.message}</p>}
          {meta.data && <p className="muted small">Backend connected. Data source: <strong>{meta.data.data_source}</strong>.</p>}
        </div>
      </div>
    </div>
  );
}

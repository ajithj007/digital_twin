from .timeutils import utcnow_iso


def log_audit(conn, actor: str, action: str, detail: str = "") -> None:
    conn.execute(
        "INSERT INTO audit_log (ts, actor, action, detail) VALUES (?,?,?,?)",
        (utcnow_iso(), actor, action, detail),
    )

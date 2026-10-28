"""Central configuration. Values can be overridden with environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = os.getenv("ASIET_DB_PATH", str(BASE_DIR / "asiet_twin.db"))

# --- security -------------------------------------------------------------
SECRET_KEY = os.getenv("ASIET_SECRET_KEY", "dev-only-secret-change-me-please-32b+")
TOKEN_EXPIRE_MINUTES = int(os.getenv("ASIET_TOKEN_EXPIRE_MINUTES", "480"))
# ESP32 devices send this key in the "X-Device-Key" header when posting readings.
DEVICE_API_KEY = os.getenv("ASIET_DEVICE_API_KEY", "esp32-dev-key")

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ASIET_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]

# --- simulator ------------------------------------------------------------
# The simulator produces SIMULATED readings (is_simulated = 1). Turn it off
# (SIMULATOR_ENABLED=0) when real hardware is connected.
SIMULATOR_ENABLED = os.getenv("SIMULATOR_ENABLED", "1") == "1"
SIMULATOR_INTERVAL_SECONDS = float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "10"))
SIMULATOR_BACKFILL_HOURS = int(os.getenv("SIMULATOR_BACKFILL_HOURS", "6"))
SIMULATOR_RANDOM_ANOMALIES = os.getenv("SIMULATOR_RANDOM_ANOMALIES", "0") == "1"

# --- data handling ----------------------------------------------------------
READINGS_RETENTION_HOURS = int(os.getenv("READINGS_RETENTION_HOURS", "24"))
DEFAULT_OFFLINE_AFTER_SECONDS = 60
ALERT_COOLDOWN_SECONDS = 120  # no new alert for the same sensor right after it was resolved
MONITOR_INTERVAL_SECONDS = 15  # how often device online/offline status is evaluated

# Used by the navigation module (estimates, labelled as such in the UI).
WALKING_SPEED_M_PER_S = 1.2
SECONDS_PER_FLOOR_TRANSITION = 20

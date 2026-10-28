# ASIET Campus Digital Twin (prototype)

IoT-enabled campus monitoring and management prototype for **Adi Shankara Institute of Engineering and Technology (ASIET), Kalady**
— final-year B.Tech CSE major project.

```
Sensors → ESP32 → Wi-Fi / HTTP → FastAPI backend → SQLite → React + React Three Fiber Digital Twin → Admin / Faculty / Student / Operations
```

> **Read this first – what is real and what is sample**
> * **Sensor data is SIMULATED** by a built-in simulator until real ESP32 hardware is connected. Every reading is stored with `is_simulated = 1`
>   and the UI shows a permanent "SIMULATED DATA" banner and SIMULATED/HARDWARE tags.
> * **The campus layout (buildings, rooms, capacities, walkways) is a SAMPLE layout**, not surveyed ASIET data. Replace it in `backend/app/campus_data.py`.
> * **The timetable is SAMPLE data**, not connected to any official ASIET system.
> * Alerts use simple threshold rules (not AI/ML). This is not a certified fire-alarm or emergency system.
> * Navigation is outdoor routing on predefined sample paths (Dijkstra). Indoor navigation is not implemented.

> **Status:** the backend logic is unit-tested; the full stack (uvicorn + Vite + browser) has not been run yet. See `docs/PROJECT_STATUS.md`.

## Quick start

You need **Python 3.10+** and **Node.js 18+**.

### 1. Backend (terminal 1)
```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate        Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
On the first start the SQLite file `backend/asiet_twin.db` is created and filled with sample data.
API docs: <http://localhost:8000/docs>

### 2. Frontend (terminal 2)
```bash
cd frontend
npm install
npm run dev
```
Open <http://localhost:5173>. The dev server forwards `/api` to `http://127.0.0.1:8000`.

### Demo accounts (prototype only)
| Role | Email | Password |
|---|---|---|
| Administrator | admin@asiet.demo | Admin@123 |
| Faculty | faculty@asiet.demo | Faculty@123 |
| Student | student@asiet.demo | Student@123 |
| Operations / Security | security@asiet.demo | Security@123 |

Login is verified by the backend (JWT). Roles are enforced in the frontend routes **and** in the backend API.

### Reset the sample database
```bash
cd backend && python -m app.seed --reset
```

## 2-minute demo script
1. Login as **Administrator** → Digital Operations Centre dashboard.
2. **Digital Twin** → click a building → a floor → a room (breadcrumbs go back). Room page shows live (simulated) values and a 2-hour chart.
3. **Incidents & Alerts** → "Demo controls" → *High temperature* for Lab 204 → wait ~10 s → alert appears (also in the bell icon).
4. **View on twin** highlights the building/room → **Acknowledge** → **Resolve**.
5. **Navigation** → From *Main Gate* To *Lab 204* → route, distance, time, floor change.
6. **Live Monitoring**, **Occupancy**, **Analytics**, **IoT Devices** (try *Device offline* in the demo controls).
7. Logout → login as **Student** (timetable, find classroom, emergency alerts, map) → **Faculty** (room availability) → **Operations** (incidents, device status).

## Project layout
```
backend/
  app/
    main.py            FastAPI app, CORS, background tasks
    config.py          settings (env variables)
    database.py        SQLite schema + connection helpers
    campus_data.py     SAMPLE campus, walkway graph, timetable generator settings, demo users, default rules
    seed.py            first-start database seeding (+ simulated history)
    simulator.py       sensor SIMULATOR + demo controls
    readings.py        storing readings (simulator + real ESP32), value validation
    alert_engine.py    threshold / over-capacity / device-offline rules
    status.py          device, room, building status
    queries.py         read-side logic used by the routers
    navigation.py      Dijkstra routing   |  timetable.py  classes & availability
    security.py, deps.py   JWT, password hashing, role checks
    routers/           auth, campus, monitoring, devices, alerts, rules, demo, routes, schedule, dashboard, admin
  tests/               test_core.py (unittest), test_api.py (pytest + TestClient)
frontend/src/
  api/client.js        every backend call
  context/, hooks/     auth + data loading hook (loading/error/polling)
  components/          layout, sidebar, search, notifications, charts, 2D map, UI parts
  three/               React Three Fiber campus scene
  pages/               Dashboard (4 roles), DigitalTwin, Monitoring, Occupancy, Incidents, Navigation, Rooms, Devices, Analytics, Settings
docs/                  ESP32_INTEGRATION.md, PROJECT_STATUS.md
```

## Main API endpoints (all under `/api`, JWT `Authorization: Bearer …`)
| Method & path | Purpose | Roles |
|---|---|---|
| POST `/auth/login`, GET `/auth/me` | login / current user | public / all |
| GET `/meta`, `/health` | data-source info, health | public |
| GET `/buildings`, `/buildings/{id}` | campus → building → floors → rooms | all |
| GET `/rooms`, `/rooms/{id}`, `/rooms/{id}/history` | room details, history | all / history: staff |
| GET `/sensors`, `/readings`, `/monitoring/series` | sensors, raw readings, chart series | staff |
| POST `/ingest` | ESP32 readings (header `X-Device-Key`) | device key |
| GET/POST `/devices`, GET `/devices/{id}` | device list / register / detail | operations, admin |
| GET `/alerts`, POST `/alerts/{id}/acknowledge`, `/resolve` | incidents | read: all (students limited) / act: operations, admin |
| GET/PUT/POST `/rules` | configurable alert rules | read: ops+admin / write: admin |
| POST `/simulator/inject` | trigger SIMULATED events for demos | operations, admin |
| GET `/navigation/locations`, `/route`, `/map` | routing | all |
| GET `/timetable`, `/timetable/availability` | sample timetable, free rooms | all |
| GET `/dashboard/summary`, `/dashboard/me`, `/analytics/overview`, `/search` | dashboards, analytics, global search | see docs |
| GET `/admin/users`, `/admin/audit` | users, audit log | admin |

## Configuration (environment variables, all optional)
`ASIET_SECRET_KEY`, `ASIET_DEVICE_API_KEY`, `SIMULATOR_ENABLED` (0 = real data only), `SIMULATOR_INTERVAL_SECONDS`, `ASIET_DB_PATH`, `ASIET_CORS_ORIGINS`, `VITE_API_BASE_URL` (frontend).
**Change the secret key and demo passwords before any real deployment.**

## Tests
```bash
cd backend
python -m unittest discover -s tests -p "test_core.py" -v   # logic: rules, routing, simulator flags, offline detection
pytest tests/test_api.py -v                                  # API: auth, roles, ingest, navigation (needs requirements.txt)
```

## Troubleshooting
* *"Cannot reach the backend"* – start `uvicorn` on port 8000 first.
* *Blank 3D area* – your browser/GPU may not support WebGL; the building list and 2D map still work.
* *No occupancy at night* – the simulator models classes Mon–Sat 08:00–18:00 IST; outside that, rooms are empty.

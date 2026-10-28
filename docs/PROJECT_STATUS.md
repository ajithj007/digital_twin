# Implementation status (keep the report consistent with this file)

Legend: **Implemented** = code exists and was exercised by the automated logic tests or by running it; **Partial**; **Not done**.
"Tested" below only means the tests in `backend/tests`.

**Verification honesty note:** this project was generated in an environment without internet access. The backend business logic
(database, simulator, alert rules, routing, timetable, role checks) was run and tested with plain Python. The FastAPI wiring was only
checked by calling the route functions directly, and the React code was only syntax-checked and bundled (imports resolved) with esbuild.
**Nothing has been run in a browser or with `uvicorn`/`npm run dev` yet**, so expect to fix small issues on the first real run, then record
real test results here.

## Implemented
- FastAPI backend with JWT login, role checks, 38 endpoints; SQLite schema (users, buildings, floors, rooms, devices, sensors, readings, alert rules, alerts, timetable, announcements, audit log)
- Sample campus data seeded on first start; simulated sensor history (6 h) and live simulator (flagged `is_simulated`)
- Sensor ingestion endpoint for real ESP32 (`/api/ingest`), device registration, value validation
- Rule-based alerts: thresholds, over-capacity (count sensors only), device offline/online; de-duplication, escalation, cooldown; acknowledge / resolve; audit log
- Building / room status (normal, attention, warning, critical, offline, not monitored) derived from alerts and devices
- React app: login, role-based sidebar and route guards, four role dashboards, global search, notification bell
- 3D Digital Twin (React Three Fiber): campus → building → floor → room, status colours, breadcrumbs, incident highlight, route overlay
- Live monitoring (filters, charts, threshold lines), occupancy, analytics, incidents, IoT devices, settings (alert rules, users, audit, system)
- Navigation: Dijkstra over sample walkway graph, distance / time / floor transition, 2D and 3D display
- Room availability search and timetable (sample data)
- Loading and error states on every data page

## Partial
- Campus model: schematic boxes and sample layout – **not** the real ASIET geometry
- Occupancy: simulated people count; real PIR sensors only give presence
- Floor plan: schematic grid of rooms, not to scale
- Navigation: outdoor graph only; floor transitions are text instructions
- Reports: analytics charts exist; no PDF/CSV export
- ESP32: backend ready, example sketch untested, no hardware results yet
- Authentication: demo accounts; no password reset, no user management UI

## Not done
- Real timetable integration, real campus survey data
- Report export (PDF/CSV), configurable rule creation in the UI (API exists), user administration
- AI / anomaly detection (deliberately excluded – rules only)
- Latency measurement, load testing, user testing, mobile polish
- Production hardening (HTTPS, secret management, DB migration)

## Wording for the report
Use "simulated" for all sensor values until hardware tests are recorded. Do not describe the threshold rules as AI. Do not claim official campus integration, certified emergency functionality or indoor navigation.

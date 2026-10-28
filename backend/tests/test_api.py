"""API tests using FastAPI's TestClient.  Run from backend/:   pytest tests/test_api.py -v
Requires:  pip install -r requirements.txt   (httpx + pytest)"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ASIET_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "api_test.db")
os.environ["SIMULATOR_ENABLED"] = "0"   # no background simulator while testing

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:   # runs the lifespan: creates + seeds the database
        yield c


def login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health_and_meta_are_public(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/meta").json()["data_source"] == "simulated"


def test_login_failure(client):
    r = client.post("/api/auth/login", json={"email": "admin@asiet.demo", "password": "wrong"})
    assert r.status_code == 401


def test_requires_authentication(client):
    assert client.get("/api/buildings").status_code == 401


def test_buildings_and_rooms(client):
    h = login(client, "admin@asiet.demo", "Admin@123")
    buildings = client.get("/api/buildings", headers=h).json()
    assert len(buildings) == 7
    detail = client.get(f"/api/buildings/{buildings[0]['id']}", headers=h).json()
    assert detail["floors"] and detail["floors"][0]["rooms"]


def test_role_restrictions(client):
    student = login(client, "student@asiet.demo", "Student@123")
    assert client.get("/api/devices", headers=student).status_code == 403
    assert client.get("/api/sensors", headers=student).status_code == 403
    assert client.get("/api/buildings", headers=student).status_code == 200
    faculty = login(client, "faculty@asiet.demo", "Faculty@123")
    assert client.post("/api/alerts/1/acknowledge", headers=faculty).status_code == 403


def test_ingest_requires_device_key(client):
    r = client.post("/api/ingest", json={"device_uid": "X", "readings": []})
    assert r.status_code == 401


def test_ingest_and_alert_flow(client):
    admin = login(client, "admin@asiet.demo", "Admin@123")
    room_id = client.get("/api/rooms", headers=admin).json()[0]["id"]
    reg = client.post("/api/devices", headers=admin, json={
        "device_uid": "ESP32-TEST", "name": "Test node", "room_id": room_id,
        "sensors": [{"type": "temperature", "unit": "°C"}]})
    assert reg.status_code == 201
    r = client.post("/api/ingest", headers={"X-Device-Key": "esp32-dev-key"},
                    json={"device_uid": "ESP32-TEST", "readings": [{"sensor_type": "temperature", "value": 40.5}]})
    assert r.status_code == 200 and r.json()["accepted"] == 1
    active = client.get("/api/alerts?status=active", headers=admin).json()
    assert any(a["alert_type"] == "high_temperature" and a["is_simulated"] == 0 for a in active)


def test_navigation_route(client):
    h = login(client, "student@asiet.demo", "Student@123")
    r = client.get("/api/navigation/route", params={"source": "node:main_gate", "destination": "building:1"}, headers=h)
    assert r.status_code == 200 and r.json()["distance_m"] > 0

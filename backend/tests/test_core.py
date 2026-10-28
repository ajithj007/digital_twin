"""Unit tests for the pure logic (no FastAPI needed):   python -m unittest discover -s tests -v   (run from backend/)"""
import os
import sys
import tempfile
import unittest
from contextlib import closing

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmp = tempfile.mkdtemp()
os.environ["ASIET_DB_PATH"] = os.path.join(_tmp, "test.db")

from app import alert_engine, navigation, queries, readings, simulator  # noqa: E402
from app.database import get_conn, init_db  # noqa: E402
from app.security import create_token, decode_token, hash_password, verify_password  # noqa: E402
from app.seed import seed_if_empty  # noqa: E402


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.conn = get_conn()
        seed_if_empty(cls.conn)
        cls.lab = cls.conn.execute("SELECT id FROM rooms WHERE code='204'").fetchone()["id"]

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_password_hash(self):
        h = hash_password("secret")
        self.assertTrue(verify_password("secret", h))
        self.assertFalse(verify_password("other", h))

    def test_token_roundtrip(self):
        self.assertEqual(decode_token(create_token(5, "admin"))["role"], "admin")
        self.assertIsNone(decode_token("garbage"))

    def test_compare(self):
        self.assertTrue(alert_engine.compare(40, ">", 38))
        self.assertFalse(alert_engine.compare(38, ">", 38))
        self.assertTrue(alert_engine.compare(1, "<=", 1))

    def test_validate_value(self):
        self.assertEqual(readings.validate_value("temperature", 25.0), "")
        self.assertNotEqual(readings.validate_value("temperature", 500), "")
        self.assertNotEqual(readings.validate_value("humidity", -5), "")
        self.assertNotEqual(readings.validate_value("temperature", "hot"), "")

    def test_dijkstra(self):
        distance, path = navigation.dijkstra("main_gate", "entrance_main")
        self.assertEqual(path[0], "main_gate")
        self.assertEqual(path[-1], "entrance_main")
        self.assertGreater(distance, 100)
        self.assertEqual(navigation.dijkstra("main_gate", "nowhere"), (None, []))

    def test_route_has_floor_transition(self):
        route = navigation.compute_route(self.conn, "node:main_gate", f"room:{self.lab}")
        self.assertEqual(route["destination"]["label"], "Lab 204")
        self.assertTrue(route["floor_transitions"])
        self.assertGreaterEqual(route["walking_time_min"], 1)

    def test_simulated_readings_are_flagged(self):
        simulator.tick(self.conn)
        flags = {r[0] for r in self.conn.execute("SELECT DISTINCT is_simulated FROM readings")}
        self.assertEqual(flags, {1})

    def test_high_temperature_creates_alert_once(self):
        simulator.inject(self.conn, "high_temperature", self.lab)
        simulator.tick(self.conn)
        simulator.tick(self.conn)
        found = self.conn.execute(
            "SELECT COUNT(*) c FROM alerts WHERE room_id=? AND alert_type='high_temperature' AND status='active'",
            (self.lab,)).fetchone()["c"]
        self.assertEqual(found, 1)  # no duplicates for the same sensor

    def test_presence_sensor_never_triggers_over_capacity(self):
        ctx = {"sensor_id": None, "device_id": None, "room_id": self.lab, "room_name": "Lab 204", "type": "occupancy",
               "unit": "presence", "sensing_mode": "presence", "capacity": 40, "building_id": 1, "floor_id": 1}
        self.assertEqual(alert_engine.evaluate_reading(self.conn, ctx, 999, False, "2026-01-01T00:00:00Z"), [])

    def test_offline_detection_and_recovery(self):
        simulator.inject(self.conn, "device_offline", self.lab)
        open_types = [a["alert_type"] for a in queries.alerts_list(self.conn, status="open")]
        self.assertIn("device_offline", open_types)
        simulator.inject(self.conn, "device_online", self.lab)
        simulator.tick(self.conn)
        open_types = [a["alert_type"] for a in queries.alerts_list(self.conn, status="open")]
        self.assertNotIn("device_offline", open_types)

    def test_student_alert_view_hides_device_details(self):
        for a in queries.alerts_list(self.conn, role="student"):
            self.assertIsNone(a["device_uid"])
            self.assertEqual(a["status"], "active")


if __name__ == "__main__":
    unittest.main()

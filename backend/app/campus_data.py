"""SAMPLE campus data used to seed the database on first start.

IMPORTANT: this is a *sample layout*, NOT surveyed ASIET data.
Building names, positions, rooms, capacities and walkways are placeholders so that the
Digital Twin can be demonstrated. Replace the values below with the real ASIET campus
information (from the campus map / department) and run:  python -m app.seed --reset

Coordinates are in metres on the campus plan: x = east/west, z = north/south
(+z points towards the Main Gate). They are only approximate.
"""

FLOOR_HEIGHT = 4.0

# room tuple: (code, name, room_type, capacity, monitored)
BUILDINGS = [
    dict(
        code="MAIN", name="Main Block (sample)",
        description="Sample academic block with classrooms, a seminar hall and Lab 204.",
        x=-45, z=55, width=56, depth=24,
        floors=[
            ("Ground Floor", [
                ("G01", "Room G01", "classroom", 60, True),
                ("G02", "Room G02", "classroom", 60, True),
                ("G03", "Staff Room", "office", 20, False),
            ]),
            ("Floor 1", [
                ("101", "Room 101", "classroom", 60, True),
                ("102", "Room 102", "classroom", 60, True),
                ("103", "Seminar Hall 1", "seminar", 100, True),
            ]),
            ("Floor 2", [
                ("201", "Room 201", "classroom", 60, True),
                ("202", "Room 202", "classroom", 60, True),
                ("204", "Lab 204", "lab", 40, True),
            ]),
        ],
    ),
    dict(
        code="CSE", name="CSE Department Block (sample)",
        description="Sample computer science block with labs and a seminar hall.",
        x=45, z=55, width=50, depth=24,
        floors=[
            ("Ground Floor", [
                ("CG1", "CSE Seminar Hall", "seminar", 120, True),
                ("CG2", "Department Office", "office", 15, False),
            ]),
            ("Floor 1", [
                ("CL1", "Programming Lab 1", "lab", 40, True),
                ("CL2", "Networks Lab", "lab", 40, True),
            ]),
            ("Floor 2", [
                ("CL3", "IoT Lab", "lab", 30, True),
                ("CL4", "Project Lab", "lab", 30, True),
                ("CR1", "Room CR1", "classroom", 60, True),
            ]),
        ],
    ),
    dict(
        code="LIB", name="Library (sample)",
        description="Sample library building.",
        x=-45, z=-12, width=50, depth=20,
        floors=[
            ("Ground Floor", [("LB0", "Reading Hall", "library", 80, True)]),
            ("Floor 1", [("LB1", "Digital Library", "library", 40, True)]),
        ],
    ),
    dict(
        code="ADMIN", name="Administration Block (sample)",
        description="Sample administrative building.",
        x=45, z=-12, width=46, depth=20,
        floors=[
            ("Ground Floor", [("AD0", "Administrative Office", "office", 25, False)]),
            ("Floor 1", [("AD1", "Conference Room", "seminar", 30, True)]),
        ],
    ),
    dict(
        code="AUD", name="Auditorium (sample)",
        description="Sample auditorium.",
        x=-45, z=-72, width=50, depth=26, height=10,
        floors=[("Ground Floor", [("AUD1", "Main Auditorium", "auditorium", 300, True)])],
    ),
    dict(
        code="LABS", name="Workshop & Labs Block (sample)",
        description="Sample workshop and electronics labs.",
        x=45, z=-72, width=46, depth=26,
        floors=[
            ("Ground Floor", [("WS1", "Workshop", "lab", 40, True)]),
            ("Floor 1", [("EL1", "Electronics Lab", "lab", 40, True)]),
        ],
    ),
    dict(
        code="CAN", name="Canteen (sample)",
        description="Sample canteen building.",
        x=-95, z=55, width=30, depth=20, height=5,
        floors=[("Ground Floor", [("CN1", "Canteen Hall", "canteen", 120, True)])],
    ),
]

# ---- walking graph used by the navigation module ---------------------------------
# key: (display name, x, z, kind)   kind: gate | junction | entrance | parking
NAV_NODES = {
    "main_gate":   ("Main Gate", 0, 125, "gate"),
    "r1_100":      ("Road Junction", 0, 100, "junction"),
    "parking":     ("Parking", 26, 100, "parking"),
    "r1_80":       ("Road Junction", 0, 80, "junction"),
    "r1_20":       ("Central Junction", 0, 20, "junction"),
    "r1_m45":      ("Road Junction", 0, -45, "junction"),
    "r1_m85":      ("North End of Main Road", 0, -85, "junction"),
    "r2_w45":      ("Road Junction", -45, 20, "junction"),
    "r2_w95":      ("Road Junction", -95, 20, "junction"),
    "r2_e45":      ("Road Junction", 45, 20, "junction"),
    "r3_w45":      ("Road Junction", -45, -45, "junction"),
    "r3_e45":      ("Road Junction", 45, -45, "junction"),
    "entrance_main":  ("Main Block entrance", -45, 38, "entrance"),
    "entrance_cse":   ("CSE Block entrance", 45, 38, "entrance"),
    "entrance_lib":   ("Library entrance", -45, 3, "entrance"),
    "entrance_admin": ("Administration Block entrance", 45, 3, "entrance"),
    "entrance_aud":   ("Auditorium entrance", -45, -52, "entrance"),
    "entrance_labs":  ("Workshop & Labs Block entrance", 45, -52, "entrance"),
    "entrance_can":   ("Canteen entrance", -95, 38, "entrance"),
}

# (node_a, node_b, kind)  kind: road | walkway   (distance is computed from coordinates)
NAV_EDGES = [
    ("main_gate", "r1_100", "road"),
    ("r1_100", "parking", "walkway"),
    ("r1_100", "r1_80", "road"),
    ("r1_80", "r1_20", "road"),
    ("r1_20", "r1_m45", "road"),
    ("r1_m45", "r1_m85", "road"),
    ("r1_20", "r2_w45", "road"),
    ("r2_w45", "r2_w95", "road"),
    ("r1_20", "r2_e45", "road"),
    ("r1_m45", "r3_w45", "road"),
    ("r1_m45", "r3_e45", "road"),
    ("r2_w45", "entrance_main", "walkway"),
    ("r2_e45", "entrance_cse", "walkway"),
    ("r2_w45", "entrance_lib", "walkway"),
    ("r2_e45", "entrance_admin", "walkway"),
    ("r3_w45", "entrance_aud", "walkway"),
    ("r3_e45", "entrance_labs", "walkway"),
    ("r2_w95", "entrance_can", "walkway"),
]

# ---- sample timetable generation -------------------------------------------------
PERIODS = [
    ("09:00", "09:50"), ("09:50", "10:40"), ("10:50", "11:40"), ("11:40", "12:30"),
    ("13:30", "14:20"), ("14:20", "15:10"), ("15:20", "16:10"),
]
CLASS_GROUPS = [
    "S7 CSE-A", "S7 CSE-B", "S5 CSE-A", "S5 CSE-B", "S3 CSE-A", "S3 CSE-B", "S1 Common-A", "S1 Common-B",
]
SAMPLE_FACULTY = [
    "Demo Faculty", "Faculty A", "Faculty B", "Faculty C", "Faculty D", "Faculty E", "Faculty F", "Faculty G",
]
THEORY_COURSES = [
    "Data Structures", "Database Management Systems", "Computer Networks", "Operating Systems",
    "Software Engineering", "Machine Learning", "Web Technologies", "Engineering Mathematics",
    "Digital Electronics", "Internet of Things",
]
LAB_COURSES = ["Programming Lab", "Networks Lab", "IoT Lab", "Electronics Lab", "Workshop Practice"]

# ---- demo accounts (DEMO ONLY - change/remove before any real deployment) --------
DEMO_USERS = [
    ("Demo Administrator", "admin@asiet.demo", "Admin@123", "admin", None),
    ("Demo Faculty", "faculty@asiet.demo", "Faculty@123", "faculty", None),
    ("Demo Student", "student@asiet.demo", "Student@123", "student", "S7 CSE-A"),
    ("Demo Security Officer", "security@asiet.demo", "Security@123", "operations", None),
]

ANNOUNCEMENTS = [
    ("Sample announcement: review schedule", "Replace this text with real announcements from the college."),
    ("Sample announcement: library timings", "Placeholder notice used to demonstrate the student dashboard."),
    ("Sample announcement: lab maintenance", "Placeholder notice. No real campus announcement is stored here."),
]

# ---- default alert rules (sample thresholds - configurable in Settings) -----------
# rule_type 'threshold': value <operator> threshold  -> alert
# rule_type 'over_capacity': occupancy count > capacity * (1 + threshold/100)
# rule_type 'device_offline': no data for `threshold` seconds -> alert
DEFAULT_RULES = [
    ("High temperature (warning)", "high_temperature", "threshold", "temperature", ">", 33, "warning",
     "Sample threshold - adjust to the room/sensor specification."),
    ("High temperature (critical)", "high_temperature", "threshold", "temperature", ">", 38, "critical",
     "Sample threshold - adjust to the room/sensor specification."),
    ("High humidity", "high_humidity", "threshold", "humidity", ">", 85, "warning",
     "Sample threshold - adjust to the room/sensor specification."),
    ("Poor air quality (warning)", "poor_air_quality", "threshold", "air_quality", ">", 1000, "warning",
     "CO2-equivalent ppm; sample threshold, adjust to the selected sensor."),
    ("Poor air quality (critical)", "poor_air_quality", "threshold", "air_quality", ">", 2000, "critical",
     "CO2-equivalent ppm; sample threshold, adjust to the selected sensor."),
    ("Over capacity", "over_capacity", "over_capacity", "occupancy", ">", 0, "warning",
     "Threshold = allowed margin above capacity in %. Only applies to sensors in 'count' mode."),
    ("Device offline", "device_offline", "device_offline", None, ">", 60, "warning",
     "Threshold = seconds without data before a device is marked offline."),
]

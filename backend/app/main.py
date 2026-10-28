"""ASIET Campus Digital Twin - FastAPI application entry point.

Run (from the backend folder):   uvicorn app.main:app --reload --port 8000
Interactive API docs:            http://localhost:8000/docs
"""
import asyncio
import logging
from contextlib import asynccontextmanager, closing

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import simulator
from .config import CORS_ORIGINS, SIMULATOR_ENABLED
from .database import get_conn, init_db
from .routers import admin, alerts, auth, campus, dashboard, demo, devices, monitoring, routes, rules, schedule
from .seed import seed_if_empty

log = logging.getLogger("asiet")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with closing(get_conn()) as conn:
        if seed_if_empty(conn):
            log.info("Sample campus data created")
    tasks = [asyncio.create_task(simulator.run_monitor())]
    if SIMULATOR_ENABLED:
        tasks.append(asyncio.create_task(simulator.run_simulator()))
        log.info("Sensor SIMULATOR is running - all generated readings are flagged as simulated")
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(
    title="ASIET Campus Digital Twin API",
    description="Prototype backend: campus data, sensor ingestion, alerts, navigation and timetable. "
                "Campus layout, timetable and (unless hardware is connected) sensor data are SAMPLE/SIMULATED.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, dashboard, campus, monitoring, devices, alerts, rules, demo, routes, schedule, admin):
    app.include_router(module.router, prefix="/api")

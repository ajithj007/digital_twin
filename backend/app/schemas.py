"""Request bodies (pydantic models). Responses are plain JSON structures built in queries.py."""
from typing import List, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class IngestReading(BaseModel):
    sensor_type: str          # temperature | humidity | occupancy | air_quality
    value: float


class IngestPayload(BaseModel):
    device_uid: str           # must match a registered device
    readings: List[IngestReading]


class SensorSpec(BaseModel):
    type: str
    unit: Optional[str] = None
    sensing_mode: str = "value"   # occupancy sensors: 'count' or 'presence'


class DeviceCreate(BaseModel):
    device_uid: str
    name: str
    room_id: int
    sensors: List[SensorSpec]


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    operator: Optional[str] = None
    threshold: Optional[float] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None


class RuleCreate(BaseModel):
    name: str
    alert_type: str
    rule_type: str = "threshold"
    sensor_type: Optional[str] = None
    operator: str = ">"
    threshold: float
    severity: str = "warning"
    description: Optional[str] = None


class InjectRequest(BaseModel):
    kind: str                 # high_temperature | over_capacity | poor_air_quality | device_offline | device_online
    room_id: int

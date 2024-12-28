import shortuuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, Float
from pydantic import BaseModel

from db import Base


class Sensors(Base):
    __tablename__ = "Sensors"

    id = Column(String, primary_key=True, index=True, default=lambda: shortuuid.uuid())
    mac_address = Column(String, nullable=False, index=True, unique=True)
    name = Column(String, nullable=False, unique=True)
    threshold_green = Column(Float, nullable=False)
    threshold_yellow = Column(Float, nullable=False)
    threshold_red = Column(Float, nullable=False, default=0)
    description = Column(String, nullable=True)


class SensorData(Base):
    __tablename__ = "SensorData"

    id = Column(String, primary_key=True, index=True, default=lambda: shortuuid.uuid())
    sensor_id = Column(String, ForeignKey("Sensors.id"), nullable=False)
    value = Column(Float, nullable=False)
    created_at = Column(String, nullable=False, default=lambda: str(datetime.now()))

# Create tables

class SensorDataRequest(BaseModel):
    mac_address: str
    value: float
    created_at: str | None = None

class SensorRequest(BaseModel):
    name: str
    threshold_green: float
    threshold_yellow: float
    threshold_red: float
    description: str
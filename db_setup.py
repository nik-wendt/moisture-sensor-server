import enum
import logging

from sqlalchemy import create_engine, Enum, Column, String, ForeignKey, Float, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
import shortuuid
from datetime import datetime

from settings import DATABASE_URL

log = logging.getLogger(__name__)

log.info("Connecting to database")
engine = create_engine(DATABASE_URL)
log.info("Connected to database")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class StatusChoices(str, enum.Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    BLACK = "black"

class Sensors(Base):
    __tablename__ = "Sensors"

    id = Column(String, primary_key=True, index=True, default=lambda: shortuuid.uuid())
    mac_address = Column(String, nullable=False, index=True, unique=True)
    name = Column(String, nullable=False, unique=True)
    threshold_green = Column(Float, nullable=False)
    threshold_yellow = Column(Float, nullable=False)
    threshold_red = Column(Float, nullable=False, default=0)
    description = Column(String, nullable=True)
    status = Column(Enum(StatusChoices), nullable=False, default=StatusChoices.BLACK)
    active = Column(Boolean, nullable=False, default=True)

    data = relationship("SensorData", back_populates="sensor")


class SensorData(Base):
    __tablename__ = "SensorData"

    id = Column(String, primary_key=True, index=True, default=lambda: shortuuid.uuid())
    sensor_id = Column(String, ForeignKey("Sensors.id"), nullable=False)
    value = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now())

    sensor = relationship("Sensors", back_populates="data")

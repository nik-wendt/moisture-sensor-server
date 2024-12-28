import shortuuid
from fastapi import APIRouter
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status

from models import Sensors, SensorData, SensorRequest, SensorDataRequest
from db import SessionLocal
router = APIRouter()

def create_sensor(mac_address: str, db_session = None):
    if not db_session:
        db_session = SessionLocal()
    id = shortuuid.uuid()
    sensor = Sensors(
        id=id,
        mac_address=mac_address,
        name=f"Unnamed Sensor - {id}",
        threshold_green=20000,
        threshold_yellow=30000,
        threshold_red=35000,
        description="A moisture sensor"
    )
    db_session.add(sensor)
    db_session.commit()
    db_session.refresh(sensor)
    return sensor

@router.post("/log")
async def log_request(log_entry: SensorDataRequest):
    """Logs incoming POST request to the database."""
    try:
        # Create a DB session
        db = SessionLocal()
        # get sensor id from mac address
        sensor = db.query(Sensors).filter(Sensors.mac_address == log_entry.mac_address).first()
        if not sensor:
            sensor = create_sensor(log_entry.mac_address, db)
        sensor_data = SensorData(
            sensor_id=sensor.id,
            value=log_entry.value,
        )

        # Add and commit the log entry to the database
        db.add(sensor_data)
        db.commit()
        db.refresh(sensor_data)
        return {"message": "Request logged successfully", "id": sensor_data.id}

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing request: {str(e)}",
        )
    finally:
        db.close()

@router.get("/sensors")
def get_sensors():
    """Returns a list of all sensors in the database."""
    try:
        # Create a DB session
        db = SessionLocal()

        # Query all sensors and append last 3 sensor readings as an average.
        sensors = db.query(Sensors).all()
        for sensor in sensors:
            sensor.readings = db.query(SensorData).filter(SensorData.sensor_id == sensor.id).order_by(SensorData.created_at.desc()).limit(3).all()
            sensor.average = sum([reading.value for reading in sensor.readings]) / len(sensor.readings)

        return {"sensors": [sensor.__dict__ for sensor in sensors]}
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    finally:
        db.close()

@router.get("/sensors/{sensor_id}")
async def get_logs(sensor_id: str):
    """Returns all log entries for a specific sensor."""
    try:
        # Create a DB session
        db = SessionLocal()

        # Query all log entries for the specified sensor
        logs = db.query(SensorData).filter(SensorData.sensor_id == sensor_id).all()

        return {"logs": [log.__dict__ for log in logs]}
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    finally:
        db.close()

import shortuuid
from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import aliased
from sqlalchemy import func, and_, case
from fastapi import HTTPException, status

from db_setup import Sensors, SensorData
from models import SensorRequest, SensorDataRequest, SensorDataFilters
from db_setup import SessionLocal
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

@router.get("/sensor-data")
async def get_sensor_data(params: SensorDataFilters = Depends()):
    try:
        # Create a DB session
        db = SessionLocal()

        latest_logs_subquery = (
            db.query(
                SensorData.sensor_id,
                func.max(SensorData.created_at).label("latest_created_at"),
            )
            .group_by(SensorData.sensor_id)
            .subquery()
        )

        # Alias for SensorData table to join with the subquery
        SensorAlias = aliased(SensorData)

        # Query to get the most recent records
        query = (
            db.query(
                # All SensorAlias fields
                SensorAlias.id,
                SensorAlias.sensor_id,
                SensorAlias.value,
                SensorAlias.created_at,
                Sensors.status.label("status"),
            )
            .join(
                latest_logs_subquery,
                and_(
                    SensorAlias.sensor_id == latest_logs_subquery.c.sensor_id,
                    SensorAlias.created_at == latest_logs_subquery.c.latest_created_at,
                ),
            )
            .join(Sensors, Sensors.id == SensorAlias.sensor_id)
        )

        # Apply filters for start_date and end_date if provided
        if params.start_date:
            query = query.filter(SensorAlias.created_at >= params.start_date)
        if params.end_date:
            query = query.filter(SensorAlias.created_at <= params.end_date)

        # Apply pagination
        logs = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()
        total = query.count()

        # Process the results
        records = [
            {
                "sensor_id": record.sensor_id,
                "value": record.value,
                "created_at": record.created_at,
                "status": record.status,
            }
            for record in logs
        ]
        return {"records": records, "total": total}

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing request: {str(e)}",
        )
    finally:
        db.close()

@router.get("/sensor-data/{sensor_id}")
async def get_logs(sensor_id: str):
    """Returns all log entries for a specific sensor."""
    try:
        # Create a DB session
        db = SessionLocal()

        # Query all log entries for the specified sensor
        logs = db.query(SensorData).filter(SensorData.sensor_id == sensor_id).all()


        return {"records": [log.__dict__ for log in logs]}
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    finally:
        db.close()

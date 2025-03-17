from datetime import datetime

from typing import Optional

import shortuuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import aliased, Session, joinedload
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
        threshold_yellow=10000,
        threshold_red=1,
        description="A moisture sensor"
    )
    db_session.add(sensor)
    db_session.commit()
    db_session.refresh(sensor)
    return sensor

@router.post("/log")
async def log_request(log_entry: SensorDataRequest):
    """Logs incoming POST request to the database."""
    max_value = 65535
    try:
        # Create a DB session
        db = SessionLocal()
        # get sensor id from mac address
        sensor = db.query(Sensors).filter(Sensors.mac_address == log_entry.mac_address).first()
        if not sensor:
            sensor = create_sensor(log_entry.mac_address, db)
        sensor_data = SensorData(
            sensor_id=sensor.id,
            value=max_value - log_entry.value,
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

@router.get("/sensor-data")
async def get_sensor_data(params: SensorDataFilters = Depends()):
    try:
        db = SessionLocal()

        latest_logs_subquery = (
            db.query(
                SensorData.sensor_id,
                func.max(SensorData.created_at).label("latest_created_at"),
            )
            .group_by(SensorData.sensor_id)
            .subquery()
        )

        # Create an alias for SensorData for the join
        SensorAlias = aliased(SensorData)

        # Query to get the most recent records with the sensor's name and status
        query = (
            db.query(
                SensorData.id,
                SensorData.sensor_id,
                SensorData.value,
                SensorData.created_at,
                Sensors.name.label("name"),
                Sensors.status.label("status"),
                Sensors.active.label("active"),
            )
            .join(Sensors, Sensors.id == SensorData.sensor_id)
            .distinct(SensorData.sensor_id)
            .order_by(
                SensorData.sensor_id,
                SensorData.created_at.desc()
            )
        )

        # Apply filters for start_date and end_date if provided
        if params.start_date:
            query = query.filter(SensorAlias.created_at >= params.start_date)
        if params.end_date:
            query = query.filter(SensorAlias.created_at <= params.end_date)

        # Apply pagination
        logs = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()
        total = query.count()

        # Process the results using the labeled "name" field
        records = [
            {
                "sensor_id": record.sensor_id,
                "value": record.value,
                "created_at": record.created_at,
                "status": record.status,
                "name": record.name,
                "active": record.active,
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
async def get_logs(
        sensor_id: str,
        start_date: Optional[datetime] = Query(None, description="Start date in ISO format"),
        end_date: Optional[datetime] = Query(None, description="End date in ISO format")):
    """Returns all log entries for a specific sensor."""
    try:
        # Create a DB session
        db = SessionLocal()

        query = (
            db.query(SensorData)
            .options(joinedload(SensorData.sensor))
            .filter(SensorData.sensor_id == sensor_id)
        )

        if start_date:
            query = query.filter(SensorData.created_at >= start_date)
        if end_date:
            query = query.filter(SensorData.created_at <= end_date)

        # Query all log entries for the specified sensor
        logs = (
            query
            .order_by(SensorData.created_at.asc())
            .all()
        )

        return {"records": [log.__dict__ for log in logs]}
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    finally:
        db.close()


@router.patch("/sensor-data/{sensor_id}")
async def update_sensor(sensor_id: str, sensor_update: SensorRequest):
    try:
        db = SessionLocal()
        sensor = db.query(Sensors).filter(Sensors.id == sensor_id).first()
        if not sensor:
            raise HTTPException(status_code=404, detail="Sensor not found")

        # Only update the fields that are provided in the request
        update_data = sensor_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(sensor, key, value)

        db.commit()
        db.refresh(sensor)
        return sensor
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    finally:
        db.close()

@router.delete("/sensors/{sensor_id}")
async def delete_sensor(sensor_id: str):
    try:
        db = SessionLocal()
        sensor = db.query(Sensors).filter(Sensors.id == sensor_id).first()
        if not sensor:
            raise HTTPException(status_code=404, detail="Sensor not found")

        db.delete(sensor)
        db.commit()
        return {"message": "Sensor deleted successfully"}
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
    finally:
        db.close()

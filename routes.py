from datetime import datetime

from typing import Optional

import shortuuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import aliased, Session, joinedload
from sqlalchemy import func, asc, desc
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

        # Create a subquery using a window function to pick the latest record per sensor.
        subq = (
            db.query(
                SensorData,
                func.row_number().over(
                    partition_by=SensorData.sensor_id,
                    order_by=SensorData.created_at.desc()
                ).label("rn")
            ).subquery()
        )

        # Query only the latest record per sensor by filtering on rn == 1.
        query = (
            db.query(
                subq.c.id,
                subq.c.sensor_id,
                subq.c.value,
                subq.c.created_at,
                Sensors.name.label("name"),
                Sensors.status.label("status"),
                Sensors.active.label("active"),
            )
            .join(Sensors, Sensors.id == subq.c.sensor_id)
            .filter(subq.c.rn == 1)
        )

        # Apply date filters if provided.
        if params.start_date:
            query = query.filter(subq.c.created_at >= params.start_date)
        if params.end_date:
            query = query.filter(subq.c.created_at <= params.end_date)

        # Apply active filter.
        # If the client does not send an "active" filter, default to active=True.
        if params.active is not None:
            query = query.filter(Sensors.active == params.active)

        # Apply sorting.
        if params.sort_by:
            if params.sort_by == "name":
                sort_field = Sensors.name
            elif params.sort_by in ["value", "created_at"]:
                # Access columns from the subquery for SensorData fields.
                sort_field = getattr(subq.c, params.sort_by)
            else:
                sort_field = subq.c.id

            sort_field = sort_field.desc() if params.order == "desc" else sort_field.asc()
            query = query.order_by(sort_field)
        else:
            # Default sorting by last updated.
            query = query.order_by(desc(subq.c.created_at))

        if params.search:
            # search by name and id
            query = query.filter(
                Sensors.name.ilike(f"%{params.search}%") | Sensors.id.ilike(f"%{params.search}%")
            )

        total = query.count()

        # Apply pagination.
        logs = query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()

        # Process the results.
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
            status_code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
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

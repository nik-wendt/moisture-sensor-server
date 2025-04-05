from typing import Optional

from fastapi import Query
from pydantic import BaseModel


# Pydantic models
class SensorDataRequest(BaseModel):
    mac_address: str
    value: float
    created_at: str | None = None
    battery: float | None = None

class SensorRequest(BaseModel):
    name: str = None
    threshold_green: float = None
    threshold_yellow: float = None
    threshold_red: float = None
    description: str = None
    active: Optional[bool] = None

class SensorDataFilters(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = Query(1, ge=1)
    page_size: int = Query(10, ge=1, le=100)
    active: Optional[bool] = None
    sort_by: Optional[str] = None
    order: Optional[str] = None
    search: Optional[str] = None

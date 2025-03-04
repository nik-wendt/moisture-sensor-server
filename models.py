from typing import Optional

from fastapi import Query
from pydantic import BaseModel


# Pydantic models
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

class SensorDataFilters(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    page: int = Query(1, ge=1)
    page_size: int = Query(10, ge=1, le=100)

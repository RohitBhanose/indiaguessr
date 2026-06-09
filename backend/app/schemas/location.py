from pydantic import BaseModel
from typing import Optional

class LocationBase(BaseModel):
    latitude: float
    longitude: float
    country: str
    state: Optional[str] = None
    city: Optional[str] = None
    mode: str
    category: str

class LocationCreate(LocationBase):
    pass

class Location(LocationBase):
    id: int

    class Config:
        from_attributes = True
        # Pydantic v2 compatible config key
        model_config = {"from_attributes": True}

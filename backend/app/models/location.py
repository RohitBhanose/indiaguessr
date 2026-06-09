from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.models.base import Base

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    country = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    mode = Column(String(50), nullable=False, index=True)      # 'india' or 'world'
    category = Column(String(50), nullable=False)  # 'urban', 'rural', 'landmark', etc.
    panorama_id = Column(String(200), nullable=True, index=True)
    verified = Column(Boolean, nullable=False, default=False, server_default="0", index=True)
    last_verified_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Location id={self.id} mode={self.mode} lat={self.latitude} lng={self.longitude}>"

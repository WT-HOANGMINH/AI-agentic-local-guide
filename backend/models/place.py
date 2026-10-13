
from sqlalchemy import Column, Integer, String, Text, Float, Boolean
from backend.database import Base


class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    address = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    price_level = Column(Integer, nullable=True)
    opening_hours = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

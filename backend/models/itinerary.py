from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(String(20), nullable=True)
    end_date = Column(String(20), nullable=True)
    total_days = Column(Integer, default=1)
    budget_level = Column(Integer, default=2)
    status = Column(String(30), default="planning")  # planning, ongoing, completed, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="itineraries")
    items = relationship("ItineraryItem", back_populates="itinerary", cascade="all, delete-orphan", order_by="ItineraryItem.day_number, ItineraryItem.order_index")


class ItineraryItem(Base):
    __tablename__ = "itinerary_items"

    id = Column(Integer, primary_key=True, index=True)
    itinerary_id = Column(Integer, ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False, index=True)
    place_id = Column(Integer, ForeignKey("places.id", ondelete="SET NULL"), nullable=True, index=True)
    day_number = Column(Integer, default=1)
    order_index = Column(Integer, default=1)
    time_slot = Column(String(50), nullable=True)  # vd: "08:30 - 11:00" hoặc "Buổi sáng"
    notes = Column(Text, nullable=True)
    estimated_cost = Column(Float, default=0.0)

    # Relationships
    itinerary = relationship("Itinerary", back_populates="items")
    place = relationship("Place")

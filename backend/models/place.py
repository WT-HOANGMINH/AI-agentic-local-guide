from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

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
    activities = Column(JSON, nullable=True)
    ticket_info = Column(String(255), nullable=True)
    ticket_source_url = Column(String(500), nullable=True)

    # Danh gia 0-5 (nhap tay tu Google Maps; NULL = chua co du lieu)
    rating = Column(Float, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    # --- Cac cot cho planner (duoc dien boi: python -m backend.enrich_places) ---
    duration_min = Column(Integer, nullable=True)     # thoi gian tham quan, phut
    open_time = Column(String(5), nullable=True)      # "07:30"
    close_time = Column(String(5), nullable=True)     # "17:00"
    best_time = Column(String(20), nullable=True)     # morning | afternoon | sunset | night
    zone = Column(String(30), nullable=True)          # trung_tam | son_tra | ba_na | hoi_an ...
    prices = relationship(
        "PlacePrice",
        back_populates="place",
        cascade="all, delete-orphan",
        order_by="PlacePrice.item_name",
        lazy="selectin",
    )


class PlacePrice(Base):
    __tablename__ = "place_prices"
    __table_args__ = (
        UniqueConstraint(
            "place_id",
            "item_name",
            "unit",
            "currency",
            name="uq_place_price_item_unit",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    place_id = Column(
        Integer,
        ForeignKey("places.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_name = Column(String(150), nullable=False)
    price_min_vnd = Column(Integer, nullable=False)
    price_max_vnd = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="VND")
    unit = Column(String(50), nullable=False)
    source_url = Column(String(500), nullable=False)
    verified_at = Column(Date, nullable=False)
    place = relationship("Place", back_populates="prices")

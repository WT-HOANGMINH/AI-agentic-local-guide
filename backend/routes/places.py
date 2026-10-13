
from math import radians, sin, cos, sqrt, atan2

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.place import Place


router = APIRouter(
    prefix="/places",
    tags=["Places"]
)


# API 1: Lay danh sach va tim kiem dia diem
@router.get("/")
def get_places(
    keyword: str | None = Query(
        default=None,
        description="Search by place name or description"
    ),
    category: str | None = Query(
        default=None,
        description="Filter by category"
    ),
    max_price: int | None = Query(
        default=None,
        ge=1,
        le=5,
        description="Maximum price level from 1 to 5"
    ),
    db: Session = Depends(get_db)
):
    query = db.query(Place).filter(Place.is_active == True)

    # Tim theo ten hoac mo ta
    if keyword:
        search_term = f"%{keyword.strip()}%"
        query = query.filter(
            (Place.name.ilike(search_term))
            | (Place.description.ilike(search_term))
        )

    # Loc theo danh muc
    if category:
        query = query.filter(
            Place.category == category.strip().lower()
        )

    # Loc theo muc gia toi da
    if max_price is not None:
        query = query.filter(
            Place.price_level <= max_price
        )

    places = query.order_by(Place.id.asc()).all()

    return {
        "total": len(places),
        "places": [
            {
                "id": place.id,
                "name": place.name,
                "category": place.category,
                "address": place.address,
                "description": place.description,
                "latitude": place.latitude,
                "longitude": place.longitude,
                "price_level": place.price_level,
                "opening_hours": place.opening_hours
            }
            for place in places
        ]
    }


# API 2: Tim dia diem gan toa do nguoi dung
# Khai bao truoc API /{place_id} de tranh trung route
@router.get("/nearby")
def get_nearby_places(
    latitude: float = Query(
        ...,
        ge=-90,
        le=90,
        description="User latitude"
    ),
    longitude: float = Query(
        ...,
        ge=-180,
        le=180,
        description="User longitude"
    ),
    radius_km: float = Query(
        default=5,
        gt=0,
        le=100,
        description="Search radius in kilometers"
    ),
    db: Session = Depends(get_db)
):
    # Tinh khoang cach bang cong thuc Haversine
    def calculate_distance(lat1, lon1, lat2, lon2):
        earth_radius = 6371

        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1))
            * cos(radians(lat2))
            * sin(dlon / 2) ** 2
        )

        # Gioi han a de tranh loi sai so so thuc
        a = max(0.0, min(1.0, a))

        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return earth_radius * c

    places = (
        db.query(Place)
        .filter(
            Place.is_active == True,
            Place.latitude.isnot(None),
            Place.longitude.isnot(None)
        )
        .all()
    )

    nearby_places = []

    for place in places:
        distance = calculate_distance(
            latitude,
            longitude,
            place.latitude,
            place.longitude
        )

        if distance <= radius_km:
            nearby_places.append({
                "id": place.id,
                "name": place.name,
                "category": place.category,
                "address": place.address,
                "description": place.description,
                "latitude": place.latitude,
                "longitude": place.longitude,
                "price_level": place.price_level,
                "opening_hours": place.opening_hours,
                "distance_km": round(distance, 2)
            })

    # Sap xep dia diem tu gan den xa
    nearby_places.sort(key=lambda item: item["distance_km"])

    return {
        "total": len(nearby_places),
        "radius_km": radius_km,
        "places": nearby_places
    }


# API 3: Lay chi tiet mot dia diem theo ID
@router.get("/{place_id}")
def get_place_detail(
    place_id: int,
    db: Session = Depends(get_db)
):
    place = (
        db.query(Place)
        .filter(
            Place.id == place_id,
            Place.is_active == True
        )
        .first()
    )

    # Khong tim thay dia diem
    if place is None:
        raise HTTPException(
            status_code=404,
            detail="Place not found"
        )

    return {
        "id": place.id,
        "name": place.name,
        "category": place.category,
        "address": place.address,
        "description": place.description,
        "latitude": place.latitude,
        "longitude": place.longitude,
        "price_level": place.price_level,
        "opening_hours": place.opening_hours
    }

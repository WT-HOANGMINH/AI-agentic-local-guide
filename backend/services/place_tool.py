
from langchain_core.tools import tool
from sqlalchemy import select, case

from backend.database import SessionLocal
from backend.models.place import Place


@tool
def search_places(
    keyword: str = "",
    category: str = "",
    max_price: int = 5,
) -> list[dict]:
    """
    Search tourist places in Da Nang from the MySQL database.

    Args:
        keyword: Keyword to search in place names.
        category: Place category, such as restaurant, cafe,
                  tourist_attraction, or shopping.
        max_price: Maximum price level, from 1 to 5.

    Returns:
        A list of matching places, prioritizing complete data.
    """

    # Validate the requested budget.
    try:
        max_price = int(max_price)
    except (TypeError, ValueError):
        max_price = 5

    max_price = max(1, min(max_price, 5))

    keyword = (keyword or "").strip()
    category = (category or "").strip()

    db = SessionLocal()

    try:
        query = select(Place).where(
            Place.is_active.is_(True)
        )

        # Search by place name.
        if keyword:
            query = query.where(
                Place.name.ilike(f"%{keyword}%")
            )

        # Filter by exact category.
        if category:
            query = query.where(
                Place.category == category
            )

        # Enforce the maximum budget.
        # Places with unknown prices are excluded.
        query = query.where(
            Place.price_level.is_not(None),
            Place.price_level <= max_price,
        )

        # Prioritize records with coordinates and addresses.
        data_completeness = (
            case(
                (
                    Place.latitude.is_not(None)
                    & Place.longitude.is_not(None),
                    1,
                ),
                else_=0,
            )
            +
            case(
                (
                    Place.address.is_not(None)
                    & (Place.address != ""),
                    1,
                ),
                else_=0,
            )
            +
            case(
                (
                    Place.description.is_not(None)
                    & (Place.description != ""),
                    1,
                ),
                else_=0,
            )
        )

        query = query.order_by(
            data_completeness.desc(),
            Place.price_level.asc(),
            Place.name.asc(),
        )

        # Return at most 10 places per tool call.
        places = db.scalars(
            query.limit(10)
        ).all()

        results = []

        for place in places:
            results.append({
                "id": place.id,
                "name": place.name,
                "category": place.category,
                "address": place.address,
                "description": place.description,
                "latitude": place.latitude,
                "longitude": place.longitude,
                "price_level": place.price_level,
                "opening_hours": place.opening_hours,
            })

        return results

    finally:
        db.close()

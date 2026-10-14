from langchain_core.tools import tool
from sqlalchemy import select

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
        A list of matching places.
    """

    db = SessionLocal()

    try:
        # Get active places from the database.
        query = select(Place).where(
            Place.is_active.is_(True)
        )

        # Filter by keyword.
        keyword = keyword.strip()

        if keyword:
            query = query.where(
                Place.name.ilike(f"%{keyword}%")
            )

        # Filter by category.
        category = category.strip()

        if category:
            query = query.where(
                Place.category == category
            )

        # Filter by maximum price level.
        query = query.where(
            (Place.price_level.is_(None))
            | (Place.price_level <= max_price)
        )

        # Limit results to 20 places before executing the query.
        places = db.scalars(
            query.limit(20)
        ).all()

        # Convert database records into dictionaries.
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
        # Close the database session.
        db.close()
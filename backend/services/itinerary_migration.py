from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_itinerary_data_column(engine: Engine) -> bool:
    """Add the structured-plan column to existing databases without replacing data."""
    inspector = inspect(engine)
    if "itineraries" not in inspector.get_table_names():
        return False
    columns = {column["name"] for column in inspector.get_columns("itineraries")}
    if "itinerary_data" in columns:
        return False

    clause = "ADD COLUMN IF NOT EXISTS" if engine.dialect.name == "postgresql" else "ADD COLUMN"
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE itineraries {clause} itinerary_data JSON"))
    return True

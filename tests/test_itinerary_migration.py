from sqlalchemy import create_engine, inspect, text

from backend.services.itinerary_migration import ensure_itinerary_data_column


def test_migration_adds_structured_data_column_to_existing_sqlite_table():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE itineraries (id INTEGER PRIMARY KEY, title VARCHAR(150))"
        ))

    assert ensure_itinerary_data_column(engine) is True
    assert "itinerary_data" in {
        column["name"] for column in inspect(engine).get_columns("itineraries")
    }
    assert ensure_itinerary_data_column(engine) is False

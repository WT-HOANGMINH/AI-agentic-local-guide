from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from backend import seed_places


def test_ensure_place_detail_columns_migrates_legacy_schema(monkeypatch, tmp_path: Path):
    database_engine = create_engine(f"sqlite:///{tmp_path / 'legacy.sqlite'}")
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE places "
                "(id INTEGER PRIMARY KEY, name VARCHAR(150) NOT NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO places (id, name) VALUES (1, 'Cầu Rồng')")
        )

    monkeypatch.setattr(seed_places, "engine", database_engine)

    seed_places.ensure_place_detail_columns()
    seed_places.ensure_place_detail_columns()

    columns = {column["name"] for column in inspect(database_engine).get_columns("places")}
    assert {
        "activities",
        "ticket_info",
        "ticket_source_url",
        "duration_min",
        "open_time",
        "close_time",
        "best_time",
        "zone",
    }.issubset(columns)

    with database_engine.connect() as connection:
        row = connection.execute(
            text("SELECT id, name FROM places WHERE id = 1")
        ).one()
    assert row == (1, "Cầu Rồng")
    database_engine.dispose()

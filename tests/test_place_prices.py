import csv
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.place import Place, PlacePrice
from backend.services.dialogue import State, handle_detail
from backend.services.place_price_import import (
    PRICE_FIELDS,
    import_place_prices,
    read_price_rows,
)


def _session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'prices.sqlite'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(
        Place(
            id=1,
            name="Cầu Rồng Đà Nẵng",
            category="tourist_attraction",
            address="Đà Nẵng",
            is_active=True,
        )
    )
    session.commit()
    return engine, session


def _write_csv(path: Path, rows: list[dict]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=sorted(PRICE_FIELDS))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _row(**overrides) -> dict:
    return {
        "place_name": "Cau Rong Da Nang",
        "item_name": "Vé tham quan",
        "price_min_vnd": "0",
        "price_max_vnd": "50000",
        "currency": "VND",
        "unit": "người",
        "source_url": "https://example.com/tickets",
        "verified_at": date.today().isoformat(),
        **overrides,
    }


def test_price_template_has_header_but_no_unverified_prices():
    template = Path(__file__).parents[1] / "backend" / "data" / "place_prices.csv"

    assert read_price_rows(template) == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"price_min_vnd": "-1"},
        {"price_min_vnd": "50000", "price_max_vnd": "1000"},
        {"currency": "USD"},
        {"source_url": "javascript:alert(1)"},
        {"verified_at": "not-a-date"},
    ],
)
def test_price_import_rejects_invalid_values(tmp_path, overrides):
    path = _write_csv(tmp_path / "prices.csv", [_row(**overrides)])

    with pytest.raises(ValueError):
        read_price_rows(path)


def test_price_import_resolves_place_and_upserts_by_item_and_unit(tmp_path):
    engine, db = _session(tmp_path)
    path = _write_csv(tmp_path / "prices.csv", [_row()])
    try:
        assert import_place_prices(db, path) == (1, 0)
        assert import_place_prices(db, path) == (0, 1)

        price = db.query(PlacePrice).one()
        assert price.place.name == "Cầu Rồng Đà Nẵng"
        assert price.price_min_vnd == 0
        assert price.price_max_vnd == 50_000
    finally:
        db.close()
        engine.dispose()


def test_price_import_rejects_unknown_place_without_partial_commit(tmp_path):
    engine, db = _session(tmp_path)
    path = _write_csv(
        tmp_path / "prices.csv",
        [_row(), _row(place_name="Không tồn tại")],
    )
    try:
        with pytest.raises(ValueError, match="not found"):
            import_place_prices(db, path)
        assert db.query(PlacePrice).count() == 0
    finally:
        db.close()
        engine.dispose()


def test_place_detail_shows_verified_price_source_and_date():
    price = SimpleNamespace(
        item_name="Vé tham quan",
        price_min_vnd=0,
        price_max_vnd=50_000,
        unit="người",
        source_url="https://example.com/tickets",
        verified_at=date(2025, 1, 2),
    )
    place = SimpleNamespace(
        id=1,
        name="Cầu Rồng",
        description="",
        open_time=None,
        close_time=None,
        opening_hours=None,
        price_level=None,
        ticket_info=None,
        ticket_source_url=None,
        prices=[price],
        address="Đà Nẵng",
        latitude=None,
        longitude=None,
    )

    response = handle_detail(State(), None, place, [])

    assert "0–50,000 VND" in response["text"]
    assert "https://example.com/tickets" in response["text"]
    assert "2025-01-02" in response["text"]


def test_place_detail_says_when_price_is_unverified():
    place = SimpleNamespace(
        id=1,
        name="Cầu Rồng",
        description="",
        open_time=None,
        close_time=None,
        opening_hours=None,
        price_level=2,
        prices=[],
        address="Đà Nẵng",
        latitude=None,
        longitude=None,
    )

    response = handle_detail(State(), None, place, [])

    assert "Chưa có giá cụ thể kèm nguồn xác minh" in response["text"]

import argparse
import csv
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from backend.models.place import Place, PlacePrice


PRICE_FIELDS = {
    "place_name",
    "item_name",
    "price_min_vnd",
    "price_max_vnd",
    "currency",
    "unit",
    "source_url",
    "verified_at",
}


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold().strip())
    normalized = "".join(
        char for char in normalized
        if unicodedata.category(char) != "Mn"
    )
    return normalized.replace("đ", "d")


def _source_url(value: str, row_number: int) -> str:
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Row {row_number}: source_url must be an absolute HTTP(S) URL.")
    return url


def _amount(value: str, field: str, row_number: int) -> int:
    try:
        amount = int(value.strip())
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"Row {row_number}: {field} must be a whole-number VND amount.") from exc
    if amount < 0:
        raise ValueError(f"Row {row_number}: {field} cannot be negative.")
    return amount


def read_price_rows(path: str | Path) -> list[dict]:
    """Read and validate the source-backed CSV without changing the database."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if (
            not reader.fieldnames
            or len(reader.fieldnames) != len(PRICE_FIELDS)
            or set(reader.fieldnames) != PRICE_FIELDS
        ):
            raise ValueError(
                "Price CSV must contain exactly these columns: "
                + ", ".join(sorted(PRICE_FIELDS))
            )

        rows = []
        seen = set()
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"Row {row_number}: unexpected extra CSV columns.")
            place_name = (row.get("place_name") or "").strip()
            item_name = (row.get("item_name") or "").strip()
            unit = (row.get("unit") or "").strip()
            currency = (row.get("currency") or "").strip().upper()
            if not place_name or not item_name or not unit:
                raise ValueError(
                    f"Row {row_number}: place_name, item_name, and unit are required."
                )
            if len(place_name) > 150 or len(item_name) > 150 or len(unit) > 50:
                raise ValueError(f"Row {row_number}: a text field exceeds its maximum length.")
            if currency != "VND":
                raise ValueError(f"Row {row_number}: currency must be VND.")

            minimum = _amount(row.get("price_min_vnd"), "price_min_vnd", row_number)
            maximum = _amount(row.get("price_max_vnd"), "price_max_vnd", row_number)
            if maximum < minimum:
                raise ValueError(
                    f"Row {row_number}: price_max_vnd cannot be lower than price_min_vnd."
                )

            try:
                verified_at = date.fromisoformat((row.get("verified_at") or "").strip())
            except ValueError as exc:
                raise ValueError(
                    f"Row {row_number}: verified_at must use YYYY-MM-DD."
                ) from exc
            if verified_at > date.today():
                raise ValueError(f"Row {row_number}: verified_at cannot be in the future.")

            source_url = _source_url(row.get("source_url") or "", row_number)
            if len(source_url) > 500:
                raise ValueError(f"Row {row_number}: source_url cannot exceed 500 characters.")
            identity = (
                _normalize_name(place_name),
                item_name.casefold(),
                unit.casefold(),
                currency,
            )
            if identity in seen:
                raise ValueError(f"Row {row_number}: duplicate price record.")
            seen.add(identity)
            rows.append({
                "place_name": place_name,
                "item_name": item_name,
                "price_min_vnd": minimum,
                "price_max_vnd": maximum,
                "currency": currency,
                "unit": unit,
                "source_url": source_url,
                "verified_at": verified_at,
            })
    return rows


def import_place_prices(db: Session, path: str | Path) -> tuple[int, int]:
    """Upsert verified source-backed prices; invalid files never partially commit."""
    rows = read_price_rows(path)
    inserted = updated = 0
    try:
        places_by_name: dict[str, list[Place]] = {}
        for place in db.query(Place).all():
            places_by_name.setdefault(_normalize_name(place.name), []).append(place)

        resolved = []
        for row_number, row in enumerate(rows, start=2):
            matches = places_by_name.get(_normalize_name(row["place_name"]), [])
            if len(matches) != 1:
                reason = "not found" if not matches else "ambiguous"
                raise ValueError(
                    f"Row {row_number}: place {row['place_name']!r} is {reason} in the database."
                )
            resolved.append((matches[0], row))

        for place, row in resolved:
            candidates = (
                db.query(PlacePrice)
                .filter_by(place_id=place.id, currency=row["currency"])
                .all()
            )
            matching_prices = [
                candidate for candidate in candidates
                if candidate.item_name.casefold() == row["item_name"].casefold()
                and candidate.unit.casefold() == row["unit"].casefold()
            ]
            if len(matching_prices) > 1:
                raise ValueError(
                    f"Multiple existing price records match {place.name}: {row['item_name']}."
                )
            price = matching_prices[0] if matching_prices else None
            if price is None:
                price = PlacePrice(
                    place_id=place.id,
                    item_name=row["item_name"],
                    price_min_vnd=row["price_min_vnd"],
                    price_max_vnd=row["price_max_vnd"],
                    currency=row["currency"],
                    unit=row["unit"],
                    source_url=row["source_url"],
                    verified_at=row["verified_at"],
                )
                db.add(price)
                inserted += 1
            else:
                for field in (
                    "price_min_vnd",
                    "price_max_vnd",
                    "source_url",
                    "verified_at",
                ):
                    setattr(price, field, row[field])
                updated += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return inserted, updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import source-verified place prices from a CSV file."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "place_prices.csv",
    )
    args = parser.parse_args()

    from backend.database import SessionLocal, engine

    PlacePrice.__table__.create(bind=engine, checkfirst=True)
    db = SessionLocal()
    try:
        inserted, updated = import_place_prices(db, args.csv_path)
    finally:
        db.close()
    print(f"Imported {inserted} new prices and updated {updated} existing prices.")


if __name__ == "__main__":
    main()

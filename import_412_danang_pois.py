import json
import re
import sys
import time
import urllib.parse
import urllib.request
import pymysql

TARGET_NEW = 412
CITY_NAME = "Da Nang"
BBOX = "15.95,108.05,16.25,108.40"
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OVERPASS_QUERY = f"""
[out:json][timeout:180];
(
  nwr["name"]["amenity"~"restaurant|cafe|fast_food|food_court|ice_cream|bar|pub|marketplace|nightclub|theatre|cinema|arts_centre|library|museum|community_centre"]({BBOX});
  nwr["name"]["shop"]({BBOX});
  nwr["name"]["tourism"~"attraction|museum|gallery|viewpoint|theme_park|zoo|aquarium"]({BBOX});
  nwr["name"]["historic"]({BBOX});
  nwr["name"]["leisure"~"park|garden|water_park|amusement_arcade|sports_centre"]({BBOX});
);
out center tags;
"""

def clean(value):
    return re.sub(r"\\s+", " ", str(value or "")).strip()

def norm(value):
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())

def get_address(tags):
    full = clean(tags.get("addr:full"))
    if full:
        return full
    parts = []
    house = clean(tags.get("addr:housenumber"))
    street = clean(tags.get("addr:street"))
    if house:
        parts.append(house)
    if street:
        parts.append(street)
    ward = clean(tags.get("addr:suburb") or tags.get("addr:quarter") or tags.get("addr:place"))
    district = clean(tags.get("addr:district"))
    city = clean(tags.get("addr:city") or tags.get("addr:province") or CITY_NAME)
    for part in (ward, district, city):
        if part and norm(part) not in {norm(x) for x in parts}:
            parts.append(part)
    if not street and not ward and not clean(tags.get("addr:place")):
        return ""
    return ", ".join(parts)

def category_for(tags):
    amenity = clean(tags.get("amenity")).lower()
    shop = clean(tags.get("shop")).lower()
    tourism = clean(tags.get("tourism")).lower()
    historic = clean(tags.get("historic")).lower()
    leisure = clean(tags.get("leisure")).lower()
    if amenity in {"restaurant", "fast_food", "food_court", "ice_cream"}:
        return "restaurant"
    if amenity in {"cafe", "bar", "pub"}:
        return "cafe"
    if shop or amenity == "marketplace":
        return "shopping"
    if tourism or historic or leisure or amenity in {
        "museum", "theatre", "cinema", "arts_centre", "library",
        "community_centre", "nightclub"
    }:
        return "tourist_attraction"
    return ""

def fetch_osm():
    payload = urllib.parse.urlencode({"data": OVERPASS_QUERY}).encode("utf-8")
    last_error = None
    for endpoint in OVERPASS_URLS:
        try:
            request = urllib.request.Request(
                endpoint, data=payload,
                headers={"User-Agent": "DaNangLocalGuidePOIImporter/1.0"}
            )
            with urllib.request.urlopen(request, timeout=210) as response:
                return json.loads(response.read().decode("utf-8")).get("elements", [])
        except Exception as exc:
            last_error = exc
            print(f"Source unavailable at {endpoint}: {exc}")
            time.sleep(2)
    raise RuntimeError(f"Could not retrieve OpenStreetMap data: {last_error}")

def element_to_record(element):
    tags = element.get("tags") or {}
    name = clean(tags.get("name") or tags.get("name:en") or tags.get("name:vi"))
    address = get_address(tags)
    category = category_for(tags)
    if not name or not address or not category:
        return None
    lat, lon = element.get("lat"), element.get("lon")
    if lat is None or lon is None:
        center = element.get("center") or {}
        lat, lon = center.get("lat"), center.get("lon")
    desc = []
    for key in ("cuisine", "shop", "tourism", "historic", "leisure", "amenity"):
        val = clean(tags.get(key))
        if val:
            desc.append(f"{key.replace('_', ' ')}: {val}")
    description = "OpenStreetMap-mapped place in Da Nang. Source tags: " + "; ".join(desc)
    opening_hours = clean(tags.get("opening_hours")) or None
    if opening_hours and len(opening_hours) > 100:
        opening_hours = opening_hours[:100]
    return {
        "name": name[:150], "category": category, "address": address[:255],
        "description": description[:2000],
        "latitude": float(lat) if lat is not None else None,
        "longitude": float(lon) if lon is not None else None,
        "price_level": None, "opening_hours": opening_hours, "is_active": 1,
    }

def main():
    print("Fetching real POIs from OpenStreetMap...")
    elements = fetch_osm()
    print(f"Downloaded {len(elements)} map features.")
    candidates, seen = [], set()
    for element in elements:
        record = element_to_record(element)
        if not record:
            continue
        key = (norm(record["name"]), norm(record["address"]))
        if key not in seen:
            seen.add(key)
            candidates.append(record)
    if not candidates:
        raise RuntimeError("No named POIs with usable address data. Nothing inserted.")

    print("\\nEnter your MySQL connection details.")
    host = input("Host [localhost]: ").strip() or "localhost"
    port = int(input("Port [3306]: ").strip() or "3306")
    user = input("Username [root]: ").strip() or "root"
    password = input("MySQL password: ")
    database = input("Database [agentic_local_guide]: ").strip() or "agentic_local_guide"

    conn = pymysql.connect(host=host, port=port, user=user, password=password,
                           database=database, charset="utf8mb4",
                           cursorclass=pymysql.cursors.DictCursor, autocommit=False)
    inserted = skipped = 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, address FROM places")
            existing = cur.fetchall()
            existing_names = {norm(r["name"]) for r in existing}
            existing_addresses = {norm(r["address"]) for r in existing if r.get("address")}
            filtered = []
            for row in candidates:
                if norm(row["name"]) in existing_names or norm(row["address"]) in existing_addresses:
                    skipped += 1
                else:
                    filtered.append(row)
            if len(filtered) < TARGET_NEW:
                raise RuntimeError(
                    f"Only {len(filtered)} new named POIs with usable addresses are available "
                    f"after deduplication; {TARGET_NEW} required. No records inserted. "
                    "Do not fabricate rows to fill the gap."
                )
            sql = """INSERT INTO places
                (name, category, address, description, latitude, longitude,
                 price_level, opening_hours, is_active)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
            for row in filtered[:TARGET_NEW]:
                cur.execute(sql, (row["name"], row["category"], row["address"],
                                  row["description"], row["latitude"], row["longitude"],
                                  row["price_level"], row["opening_hours"], row["is_active"]))
                inserted += 1
            cur.execute("SELECT COUNT(*) AS total FROM places")
            total = cur.fetchone()["total"]
            conn.commit()
            print("\\nIMPORT SUCCESS")
            print(f"New rows inserted: {inserted}")
            print(f"Duplicates skipped: {skipped}")
            print(f"Total rows now in places: {total}")
            cur.execute("SELECT category, COUNT(*) AS total FROM places GROUP BY category ORDER BY total DESC")
            for row in cur.fetchall():
                print(f"{row['category']}: {row['total']}")
    except Exception as exc:
        conn.rollback()
        print("\\nIMPORT CANCELLED; transaction rolled back.")
        print(exc)
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()

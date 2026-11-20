from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import seed_places
from backend.auth_utils import get_current_user
from backend.database import Base, get_db
from backend.main import app
from backend.models.place import Place
from backend.models.user import User
from backend.routes import itineraries as itinerary_routes


def test_smart_itinerary_deduplicates_and_preserves_weather_metadata(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)()
    user = User(
        username="smart-itinerary-test",
        email="smart-itinerary-test@example.invalid",
        password="test-password",
    )
    test_session.add_all([
        user,
        Place(
            id=1001, name="Bãi biển Mỹ Khê", category="tourist_attraction",
            address="Đà Nẵng", is_active=True, weather_profile="outdoor",
        ),
        Place(
            id=1002, name="Bảo tàng Chăm", category="tourist_attraction",
            address="Đà Nẵng", is_active=True, weather_profile="indoor",
        ),
        Place(
            id=1003, name="Quán ăn Đà Nẵng", category="restaurant",
            address="Đà Nẵng", is_active=True, weather_profile="indoor",
        ),
        Place(
            id=1004, name="Cà phê sân vườn", category="cafe",
            address="Đà Nẵng", is_active=True, weather_profile="outdoor",
        ),
        Place(
            id=1005, name="Cà phê trong nhà", category="cafe",
            address="Đà Nẵng", is_active=True, weather_profile="indoor",
        ),
    ])
    test_session.commit()
    test_session.refresh(user)

    def override_db():
        db = sessionmaker(bind=engine)()
        try:
            yield db
        finally:
            db.close()

    first_day = date(2026, 7, 1)
    hours = []
    daily = []
    for offset in range(2):
        target = first_day + timedelta(days=offset)
        iso = target.isoformat()
        for hour in range(24):
            rainy = offset == 0 and 14 <= hour < 18
            hours.append({
                "time": f"{iso}T{hour:02d}:00",
                "temp_c": 27,
                "feels_like_c": 29,
                "rain_prob": 85 if rainy else 5,
                "rain_mm": 9.0 if rainy else 0.0,
                "weather_code": 65 if rainy else 1,
                "wind_kmh": 10,
                "gust_kmh": 18,
            })
        daily.append({
            "date": iso,
            "temp_min": 25,
            "temp_max": 31,
            "rain_prob_max": 85,
            "rain_sum_mm": 36.0,
        })
    monkeypatch.setattr(
        itinerary_routes,
        "get_weather_forecast",
        lambda **kwargs: {
            "hours": hours,
            "daily": daily,
            "source": "Open-Meteo",
            "fetched_at": "2026-06-30T12:00+07:00",
            "is_stale": False,
            "from_cache": False,
        },
    )
    monkeypatch.setattr(seed_places, "engine", engine)

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        response = TestClient(app).post(
            "/itineraries/generate-smart",
            json={"days": 2, "travel_date": first_day.isoformat()},
        )
        assert response.status_code == 201, response.text
        saved = response.json()
        items = saved["itinerary_data"]["days"]
        place_ids = [
            item["place_id"]
            for day in items
            for item in day["items"]
            if item["place_id"] is not None
        ]
        assert len(place_ids) == len(set(place_ids))
        assert saved["start_date"] == first_day.isoformat()
        assert saved["end_date"] == (first_day + timedelta(days=1)).isoformat()
        assert saved["itinerary_data"]["preferences"]["weather_source"] == "Open-Meteo"
        assert items[0]["items"][2]["title"] == "Cà phê trong nhà"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        test_session.close()
        engine.dispose()

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth_utils import get_current_user
from backend.database import Base, get_db
from backend.main import app
from backend.models.user import User


def test_chat_itinerary_is_saved_with_structured_plan_and_items():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)()
    user = User(
        username="itinerary-test",
        email="itinerary-test@example.invalid",
        password="test-password",
    )
    admin = User(
        username="itinerary-admin-test",
        email="itinerary-admin-test@example.invalid",
        password="test-password",
        role="admin",
    )
    test_session.add_all([user, admin])
    test_session.commit()
    test_session.refresh(user)
    test_session.refresh(admin)

    def override_db():
        db = sessionmaker(bind=engine)()
        try:
            yield db
        finally:
            db.close()

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    plan = {
        "title": "Cuối tuần Đà Nẵng",
        "duration_days": 1,
        "budget": {"amount": 500000, "currency": "VND", "level": "low"},
        "days": [{
            "day_number": 1,
            "items": [{
                "order": 1,
                "kind": "visit",
                "title": "Ngắm biển",
                "start_time": "08:00",
                "end_time": "10:00",
                "address": "Bãi biển Mỹ Khê",
            }],
        }],
    }

    try:
        response = TestClient(app).post(
            "/itineraries/from-chat",
            json={"itinerary": plan},
        )
        assert response.status_code == 201, response.text
        saved = response.json()
        assert saved["itinerary_data"]["title"] == plan["title"]
        assert len(saved["itinerary_data"]["days"][0]["items"]) == 1
        assert len(saved["items"]) == 1
        assert saved["items"][0]["notes"].startswith("Ngắm biển")

        replaced = TestClient(app).put(
            f"/itineraries/{saved['id']}/items",
            json={"items": [{
                "place_id": None,
                "day_number": 1,
                "order_index": 1,
                "time_slot": "10:00 - 11:00",
                "notes": "Ghi chú",
            }]},
        )
        assert replaced.status_code == 200, replaced.text
        assert replaced.json()["itinerary_data"]["days"][0]["items"][0]["description"] == "Ghi chú"

        duplicate = TestClient(app).post(
            "/itineraries/from-chat",
            json={"itinerary": plan},
        )
        assert duplicate.status_code == 201, duplicate.text
        assert duplicate.json()["id"] == saved["id"]

        distinct_plan = {**plan, "original_request": "Lịch trình khác cùng tên"}
        distinct = TestClient(app).post(
            "/itineraries/from-chat",
            json={"itinerary": distinct_plan},
        )
        assert distinct.status_code == 201, distinct.text
        assert distinct.json()["id"] != saved["id"]

        deleted = TestClient(app).delete(f"/itineraries/{saved['id']}")
        assert deleted.status_code == 200, deleted.text
        recreated = TestClient(app).post(
            "/itineraries/from-chat",
            json={"itinerary": plan},
        )
        assert recreated.status_code == 201, recreated.text
        assert recreated.json()["id"] != saved["id"]

        app.dependency_overrides[get_current_user] = lambda: admin
        assert TestClient(app).get(f"/itineraries/{recreated.json()['id']}").status_code == 403
        assert TestClient(app).delete(f"/itineraries/{recreated.json()['id']}").status_code == 403
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        test_session.close()
        engine.dispose()

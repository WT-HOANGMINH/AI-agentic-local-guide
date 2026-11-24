from backend.routes import ai_guide
from backend.services.dialogue import State


class FakeSession:
    def close(self):
        pass


def test_standalone_weather_phrase_overrides_classifier_and_uses_weather_service(monkeypatch):
    calls = {}
    monkeypatch.setattr(ai_guide, "is_ollama_available", lambda: False)
    monkeypatch.setattr(
        ai_guide,
        "predict_intent",
        lambda message: {"intent": "out_of_scope", "confidence": 0.4},
    )
    monkeypatch.setattr(ai_guide, "SessionLocal", FakeSession)

    def weather_reply(message, intent, state, db):
        calls.update(message=message, intent=intent, db=db)
        return {
            "text": "Dự báo",
            "steps": [],
            "suggestions": [],
            "links": [],
            "weather": {"cache_status": "fresh"},
            "_skip_llm": True,
        }

    monkeypatch.setattr(ai_guide, "maybe_weather_reply", weather_reply)
    monkeypatch.setattr(
        ai_guide,
        "respond",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("dialogue should not handle standalone weather")),
    )

    state = State()
    result = ai_guide._compute("Mai Đà Nẵng có mưa không?", state)

    assert calls["intent"] == "weather"
    assert calls["message"] == "Mai Đà Nẵng có mưa không?"
    assert result["intent"] == "weather"
    assert result["weather"]["cache_status"] == "fresh"


def test_itinerary_bound_weather_uses_dialogue_planner_without_duplicate_fetch(monkeypatch):
    calls = {"weather_helper": 0, "dialogue": 0}
    monkeypatch.setattr(ai_guide, "is_ollama_available", lambda: False)
    monkeypatch.setattr(
        ai_guide,
        "predict_intent",
        lambda message: {"intent": "unclear", "confidence": 0.2},
    )
    monkeypatch.setattr(ai_guide, "SessionLocal", FakeSession)

    def weather_reply(*args, **kwargs):
        calls["weather_helper"] += 1
        return None

    def dialogue_reply(state, message, intent, confidence, db, **kwargs):
        calls["dialogue"] += 1
        assert intent == "weather"
        return {
            "text": "Đã kiểm tra lịch trình",
            "steps": [],
            "suggestions": [],
            "links": [],
            "itinerary": {"days": []},
        }

    monkeypatch.setattr(ai_guide, "maybe_weather_reply", weather_reply)
    monkeypatch.setattr(ai_guide, "respond", dialogue_reply)

    state = State(plan=[{"stops": []}])
    result = ai_guide._compute("Nếu mưa thì sao?", state)

    assert calls == {"weather_helper": 0, "dialogue": 1}
    assert result["intent"] == "weather"
    assert "itinerary" in result

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.routes import ai_guide, auth
from backend.routes.ai_guide import ChatRequest
from backend.services import llm_service


def test_request_analysis_uses_validated_json_and_conversation_history(monkeypatch):
    request = {}

    def chat_once(messages, **kwargs):
        request["messages"] = messages
        request["kwargs"] = kwargs
        return '{"intent":"general","confidence":0.97,"requires_local_data":false}'

    monkeypatch.setattr(llm_service, "_chat_once", chat_once)

    result = llm_service.analyze_request(
        "Mặc gì cho chuyến đi?",
        history=[
            {"role": "user", "content": "Tôi đi Đà Nẵng 3 ngày"},
            {"role": "assistant", "content": "Mình có thể giúp bạn chuẩn bị."},
        ],
    )

    assert result.intent == "general"
    assert result.requires_local_data is False
    assert request["kwargs"]["schema"]["title"] == "RequestAnalysis"
    prompt = str(request["messages"])
    assert "Tôi đi Đà Nẵng 3 ngày" in prompt
    assert "Mặc gì cho chuyến đi?" in prompt


def test_chat_request_requires_latitude_and_longitude_as_a_pair():
    assert ChatRequest(message="Tìm quán gần tôi").latitude is None
    with pytest.raises(ValueError):
        ChatRequest(message="Tìm quán gần tôi", latitude=16.0)
    with pytest.raises(ValueError):
        ChatRequest(message="Tìm quán gần tôi", longitude=108.0)


def test_nearby_query_forces_local_route_when_classifier_says_general(monkeypatch):
    observed = {}

    class FakeDatabase:
        def close(self):
            pass

    def respond(state, message, intent, confidence, db, **kwargs):
        observed.update(intent=intent, pos=state.pos, lat=kwargs["lat"], lng=kwargs["lng"])
        return {"text": "Verified nearby places", "steps": []}

    monkeypatch.setattr(ai_guide, "_route", lambda message, state: ("general", 0.9, "ollama"))
    monkeypatch.setattr(ai_guide, "SessionLocal", FakeDatabase)
    monkeypatch.setattr(ai_guide, "respond", respond)

    result = ai_guide._compute(
        "Find places near here",
        ai_guide.State(),
        16.06,
        108.22,
    )

    assert result["intent"] == "attraction"
    assert result["router"] == "local"
    assert observed == {
        "intent": "attraction",
        "pos": (16.06, 108.22),
        "lat": 16.06,
        "lng": 108.22,
    }


def test_general_chat_uses_llm_analysis_without_intent_classifier(monkeypatch):
    monkeypatch.setattr(ai_guide, "is_ollama_available", lambda: True)
    monkeypatch.setattr(
        ai_guide,
        "analyze_request",
        lambda message, history: llm_service.RequestAnalysis(
            intent="general",
            confidence=0.97,
            requires_local_data=False,
        ),
    )
    monkeypatch.setattr(
        ai_guide,
        "predict_intent",
        lambda message: (_ for _ in ()).throw(
            AssertionError("classifier should not route LLM-analyzed requests")
        ),
    )
    monkeypatch.setattr(
        ai_guide,
        "ask_llm",
        lambda message, history=None, grounded_answer=None: (
            "Bạn nên chuẩn bị trang phục thoải mái."
        ),
    )

    response = TestClient(app).post(
        "/api/ai-guide/chat",
        json={"message": "Tôi nên mặc gì khi đi du lịch?"},
    )

    assert response.status_code == 200
    assert response.json()["intent"] == "general"
    assert response.json()["reply"] == "Bạn nên chuẩn bị trang phục thoải mái."


def test_verified_nearby_results_skip_llm_rewriting(monkeypatch):
    monkeypatch.setattr(ai_guide, "is_ollama_available", lambda: True)

    mode = ai_guide._llm_mode({
        "_skip_llm": True,
        "status": "completed",
        "intent": "attraction",
        "text": "Khoảng cách Haversine và thứ tự POI",
    })

    assert mode == "skip"


def test_ollama_stream_yields_only_user_facing_model_output(monkeypatch):
    request = {}

    def stream_chat(messages, **kwargs):
        request["messages"] = messages
        yield "Câu trả lời"
        yield " đã xác minh"

    monkeypatch.setattr(llm_service, "_stream_chat", stream_chat)

    result = list(llm_service.stream_grounded_answer("Câu hỏi", "Dữ liệu thật"))

    assert result == ["Câu trả lời", " đã xác minh"]
    assert "Dữ liệu thật" in str(request["messages"])


def test_local_frontend_origin_can_use_session_cookie():
    client = TestClient(app)
    response = client.post(
        "/auth/logout",
        headers={"Origin": "http://127.0.0.1:5500"},
        cookies={"danang_session": "test-session"},
    )
    assert response.status_code == 204


def test_untrusted_origin_is_rejected_for_session_cookie():
    client = TestClient(app)
    response = client.post(
        "/auth/logout",
        headers={"Origin": "https://untrusted.example"},
        cookies={"danang_session": "test-session"},
    )
    assert response.status_code == 403


def test_production_csrf_allows_configured_frontend_origin(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", "https://guide.example")
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://api.example")
    response = TestClient(app).post(
        "/auth/logout",
        headers={"Origin": "https://guide.example"},
        cookies={"danang_session": "test-session"},
    )
    assert response.status_code == 204


def test_production_csrf_allows_configured_frontend_origin_with_path(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", "https://guide.example/app")
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://api.example")
    response = TestClient(app).post(
        "/auth/logout",
        headers={"Origin": "https://guide.example"},
        cookies={"danang_session": "test-session"},
    )
    assert response.status_code == 204


def test_production_csrf_rejects_unconfigured_origin(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", "https://guide.example")
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://api.example")
    response = TestClient(app).post(
        "/auth/logout",
        headers={"Origin": "https://attacker.example"},
        cookies={"danang_session": "test-session"},
    )
    assert response.status_code == 403


def test_chat_stream_marks_non_streaming_fallback(monkeypatch):
    monkeypatch.setattr(ai_guide, "is_ollama_available", lambda: False)
    monkeypatch.setattr(
        ai_guide,
        "_compute",
        lambda message, state, lat=None, lng=None, on_step=None: {
            "steps": ["Đang truy cập dữ liệu"],
            "text": "Suggested places",
            "intent": "attraction",
            "confidence": 1.0,
            "status": "completed",
            "suggestions": [],
        },
    )

    client = TestClient(app)
    response = client.post(
        "/api/ai-guide/chat-stream",
        json={"message": "places", "session_id": "stream-fallback-test"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type": "result"' in response.text
    assert '"streaming": false' in response.text
    assert '"phase": "received"' in response.text
    assert '"phase": "analyzing"' in response.text
    assert '"phase": "analyzed"' in response.text
    assert '"completed": true' in response.text
    assert '"text": "Đã truy cập dữ liệu"' in response.text
    assert (
        response.text.index('"phase": "received"')
        < response.text.index('"phase": "analyzing"')
    )
    assert (
        response.text.index('"phase": "analyzing"')
        < response.text.index('"phase": "analyzed"')
    )
    assert (
        response.text.index('"phase": "analyzed"')
        < response.text.index('"completed": true')
    )
    assert "Gemini" not in response.text
    assert '"type": "token"' not in response.text
    assert '"type": "done"' in response.text


def test_chat_stream_hides_place_count_in_progress_step(monkeypatch):
    monkeypatch.setattr(ai_guide, "is_ollama_available", lambda: False)
    monkeypatch.setattr(
        ai_guide,
        "_compute",
        lambda message, state, lat=None, lng=None, on_step=None: {
            "steps": ["Đang truy cập cơ sở dữ liệu địa điểm (49 địa điểm)"],
            "text": "Suggested places",
            "intent": "attraction",
            "confidence": 1.0,
            "status": "completed",
            "suggestions": [],
        },
    )

    response = TestClient(app).post(
        "/api/ai-guide/chat-stream",
        json={"message": "places", "session_id": "stream-place-count-test"},
    )

    assert response.status_code == 200
    assert '"text": "Đã truy cập cơ sở dữ liệu địa điểm"' in response.text
    assert "(49 địa điểm)" not in response.text


def test_google_oauth_reports_missing_configuration(monkeypatch):
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_SECRET", "")
    response = TestClient(app).get("/auth/google/url")
    assert response.status_code == 503
    assert "GOOGLE_CLIENT_ID" in response.json()["error"]


def test_google_oauth_url_uses_state_cookie(monkeypatch):
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(auth, "GOOGLE_CLIENT_SECRET", "test-client-secret")
    response = TestClient(app).get("/auth/google/url")
    assert response.status_code == 200
    assert response.json()["auth_url"].startswith(
        "https://accounts.google.com/o/oauth2/v2/auth?"
    )
    assert "google_oauth_state=" in response.headers["set-cookie"]
    assert "state=" in response.json()["auth_url"]


def test_google_oauth_callback_rejects_missing_state():
    response = TestClient(app).get(
        "/auth/google/callback",
        params={"code": "test-code", "state": "unmatched-state"},
    )
    assert response.status_code == 400


def test_production_oauth_session_cookie_supports_cross_site_frontend(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(auth, "IS_PRODUCTION", True)
    user = SimpleNamespace(id=1, username="oauth-user", role="user")
    response = auth._oauth_session_response(user, "google")

    session_cookie = response.headers["set-cookie"].lower()
    assert "samesite=none" in session_cookie
    assert "secure" in session_cookie
    assert "httponly" in session_cookie


def test_facebook_oauth_reports_missing_configuration(monkeypatch):
    monkeypatch.delenv("FACEBOOK_APP_ID", raising=False)
    monkeypatch.delenv("FACEBOOK_APP_SECRET", raising=False)
    response = TestClient(app).get("/auth/facebook/url")
    assert response.status_code == 503
    assert "FACEBOOK_APP_ID" in response.json()["error"]


def test_facebook_oauth_callback_rejects_missing_state():
    response = TestClient(app).get(
        "/auth/facebook/callback",
        params={"code": "test-code", "state": "unmatched-state"},
    )
    assert response.status_code == 400


def test_facebook_oauth_url_uses_state_cookie(monkeypatch):
    monkeypatch.setenv("FACEBOOK_APP_ID", "test-app-id")
    monkeypatch.setenv("FACEBOOK_APP_SECRET", "test-app-secret")
    response = TestClient(app).get("/auth/facebook/url")
    assert response.status_code == 200
    assert response.json()["auth_url"].startswith(
        "https://www.facebook.com/v24.0/dialog/oauth?"
    )
    assert "facebook_oauth_state=" in response.headers["set-cookie"]
    assert "state=" in response.json()["auth_url"]

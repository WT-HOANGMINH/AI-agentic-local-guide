from fastapi.testclient import TestClient

from backend.main import app
from backend.routes import ai_guide, auth
from backend.services import llm_service


def test_gemini_stream_yields_only_user_facing_model_output(monkeypatch):
    from types import SimpleNamespace

    events = [
        SimpleNamespace(
            event_type="step.start",
            index=0,
            step=SimpleNamespace(type="thought"),
        ),
        SimpleNamespace(
            event_type="step.delta",
            index=0,
            delta=SimpleNamespace(type="text", text="private thought"),
        ),
        SimpleNamespace(
            event_type="step.start",
            index=1,
            step=SimpleNamespace(type="model_output"),
        ),
        SimpleNamespace(
            event_type="step.delta",
            index=1,
            delta=SimpleNamespace(type="text", text="Câu trả lời"),
        ),
        SimpleNamespace(
            event_type="step.delta",
            index=1,
            delta=SimpleNamespace(type="text", text=" đã xác minh"),
        ),
    ]
    request = {}
    client = SimpleNamespace(
        interactions=SimpleNamespace(
            create=lambda **kwargs: (request.update(kwargs) or events)
        )
    )
    monkeypatch.setattr(llm_service, "get_gemini_client", lambda: client)

    result = list(llm_service.stream_grounded_answer("Câu hỏi", "Dữ liệu thật"))

    assert result == ["Câu trả lời", " đã xác minh"]
    assert request["stream"] is True
    assert request["input"].endswith("Dữ liệu thật")


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
    monkeypatch.setattr(ai_guide, "is_gemini_configured", lambda: False)
    monkeypatch.setattr(
        ai_guide,
        "_compute",
        lambda message, state, lat=None, lng=None, on_step=None: {
            "steps": ["Place lookup complete"],
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
    assert "Gemini" not in response.text
    assert '"type": "token"' not in response.text
    assert '"type": "done"' in response.text


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

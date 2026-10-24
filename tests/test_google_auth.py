import unittest
from fastapi.testclient import TestClient
from backend.main import app

class TestGoogleAuth(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_google_login_new_user(self):
        payload = {
            "email": "test.google.new@example.com",
            "name": "Test Google User",
            "picture": "https://example.com/avatar.jpg",
            "google_id": "google_123456789"
        }
        response = self.client.post("/auth/google", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["email"], "test.google.new@example.com")

    def test_google_login_existing_user(self):
        payload = {
            "email": "test.google.new@example.com",
            "name": "Test Google User Updated",
            "picture": "https://example.com/avatar_new.jpg"
        }
        response = self.client.post("/auth/google", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["email"], "test.google.new@example.com")

    def test_google_login_missing_info(self):
        payload = {}
        response = self.client.post("/auth/google", json=payload)
        self.assertEqual(response.status_code, 400)

if __name__ == "__main__":
    unittest.main()

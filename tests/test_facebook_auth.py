import unittest
from fastapi.testclient import TestClient
from backend.main import app

class TestFacebookAuth(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_facebook_login_new_user(self):
        payload = {
            "email": "test.facebook.new@example.com",
            "name": "Test Facebook User",
            "picture": "https://example.com/fb_avatar.jpg",
            "facebook_id": "1092777120272337_999"
        }
        response = self.client.post("/auth/facebook", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["email"], "test.facebook.new@example.com")
        self.assertEqual(data["token_type"], "bearer")

    def test_facebook_login_existing_user(self):
        payload = {
            "email": "test.facebook.new@example.com",
            "name": "Test Facebook User Updated",
            "facebook_id": "1092777120272337_999"
        }
        response = self.client.post("/auth/facebook", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["email"], "test.facebook.new@example.com")

    def test_facebook_login_with_facebook_id_only(self):
        # Case where Facebook doesn't return email (e.g. phone-only account)
        payload = {
            "name": "Facebook User No Email",
            "facebook_id": "9876543210123"
        }
        response = self.client.post("/auth/facebook", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertTrue(data["email"].startswith("fb_9876543210123@facebook.com"))

    def test_facebook_login_missing_info(self):
        payload = {}
        response = self.client.post("/auth/facebook", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_facebook_auth_url(self):
        response = self.client.get("/auth/facebook/url")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["client_id"], "1092777120272337")
        self.assertIn("1092777120272337", data["auth_url"])
        self.assertIn("facebook.com", data["auth_url"])

if __name__ == "__main__":
    unittest.main()

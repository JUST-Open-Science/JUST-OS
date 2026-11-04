import os
import unittest
from unittest.mock import patch

from just_os.app import FlaskApp


class DummyLimiter:
    def limit(self, _limit):
        return lambda view: view


class DummyRateLimitManager:
    def __init__(self, app, config):
        self.limiter = DummyLimiter()

    def get_chat_rate_limit(self):
        return None


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"SECRET_KEY": "test-secret", "JUST_OS_SECURE_COOKIES": "true"})
        self.env.start()
        self.addCleanup(self.env.stop)
        with patch("just_os.app.RateLimitManager", DummyRateLimitManager), patch("just_os.app.ChatManager"):
            self.app = FlaskApp().app
        self.client = self.app.test_client()

    def test_background_color_rejects_injection(self):
        response = self.client.get("/", query_string={"bg_color": "red;}</style><script>alert(1)</script>"})
        self.assertNotIn(b"<script>alert(1)</script>", response.data)
        self.assertIn(b"background-color: #fefdf6", response.data)

    def test_chat_rejects_bad_types_and_ids(self):
        for payload in ({"message": [], "chat_id": "abc"}, {"message": "hello", "chat_id": "../bad"}):
            response = self.client.post("/chat", json=payload)
            self.assertEqual(response.status_code, 400)
            if "Set-Cookie" in response.headers:
                cookie = response.headers["Set-Cookie"]
        self.assertIn("Secure", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)

    def test_required_secret_fails_closed(self):
        with patch.dict(os.environ, {"JUST_OS_REQUIRE_SECRET": "true"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
                FlaskApp()


if __name__ == "__main__":
    unittest.main()

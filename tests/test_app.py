"""Smoke tests for the Personalized Workout Generator.

Run from the project root:

    python -m unittest discover -s tests -v

The default tests never call the real Gemini API - ``app.query_gemini`` is patched
with a stub. Set ``RUN_LIVE_GEMINI_TEST=1`` to also run the two live tests: one that
checks a rejected API key maps to a safe 503, and one real generation (which needs a
valid ``GEMINI_API_KEY``).
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

# The app requires these variables at import time; provide test values first.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("GEMINI_API_KEY", "test-api-key")
os.environ.setdefault("FLASK_DEBUG", "false")

import app as workout_app  # noqa: E402  (import must happen after env vars are set)

SAMPLE_PLAN = """# Push Day

- Push-up 3 x 12
- Squat 3 x 10
- Plank 60 seconds

Finish with a short cool-down.
"""

VALID_FORM = {
    "goal": "fat loss",
    "time": "30",
    "weight": "75",
    "height": "180",
    "age": "30",
    "gender": "male",
    "level": "beginner",
    "equipment": "Dumbbells",
}


class WorkoutAppTestCase(unittest.TestCase):
    """Tests the Flask routes with a stubbed Gemini call."""

    def setUp(self):
        # CSRF is covered by its own test; keep the other tests focused.
        workout_app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = workout_app.app.test_client()

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def plan_response(*_args, **_kwargs):
        return SAMPLE_PLAN

    # ------------------------------------------------------------------ tests
    def test_index_renders_form_with_csrf_token(self):
        response = self.client.get("/")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('action="/generate"', body)
        self.assertIn('name="csrf_token"', body)

    def test_generate_returns_plan_for_valid_input(self):
        with mock.patch.object(workout_app, "query_gemini",
                               side_effect=self.plan_response):
            response = self.client.post("/generate", data=VALID_FORM)

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("<h1>Push Day</h1>", body)
        self.assertIn("youtube.com/embed", body)  # matched exercise videos

    def test_generate_rejects_invalid_input(self):
        invalid = dict(VALID_FORM, age="200")

        response = self.client.post("/generate", data=invalid)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Age must be between 13 and 120 years",
                      response.get_data(as_text=True))

    def test_generate_returns_503_when_gemini_fails(self):
        """A failed Gemini call must be reported, never silently swallowed."""
        with mock.patch.object(
                workout_app, "query_gemini",
                side_effect=workout_app.GeminiError("api_error", "Unable to generate workout.")):
            response = self.client.post("/generate", data=VALID_FORM)

        self.assertEqual(response.status_code, 503)
        self.assertIn("Unable to generate workout.",
                      response.get_data(as_text=True))

    def test_generate_requires_csrf_token(self):
        workout_app.app.config["WTF_CSRF_ENABLED"] = True
        try:
            response = self.client.post("/generate", data=VALID_FORM)
        finally:
            workout_app.app.config["WTF_CSRF_ENABLED"] = False

        self.assertEqual(response.status_code, 400)
        self.assertIn("CSRF", response.get_data(as_text=True))

    def test_query_gemini_without_api_key_raises_gemini_error(self):
        original_key = workout_app.api_key
        workout_app.api_key = None
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}, clear=True):
            try:
                with self.assertRaises(workout_app.GeminiError) as ctx:
                    workout_app.query_gemini("test prompt")
            finally:
                workout_app.api_key = original_key

        self.assertEqual(ctx.exception.kind, "not_configured")


    def test_classify_gemini_error_maps_status_codes(self):
        class FakeError(Exception):
            def __init__(self, code, message):
                super().__init__(message)
                self.code = code

        self.assertEqual(
            workout_app.classify_gemini_error(FakeError(404, "model not found"))[0],
            "model_unavailable")
        self.assertEqual(
            workout_app.classify_gemini_error(FakeError(429, "quota exceeded"))[0],
            "quota_exceeded")
        self.assertEqual(
            workout_app.classify_gemini_error(FakeError(None, "API key not valid"))[0],
            "invalid_api_key")

    def test_get_api_key_sanitizes_quotes_and_whitespace(self):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": '  "AIzaTestKey123"  '}, clear=True):
            workout_app.api_key = None
            self.assertEqual(workout_app.get_api_key(), "AIzaTestKey123")

        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "  'AIzaTestKey456'  "}, clear=True):
            workout_app.api_key = None
            self.assertEqual(workout_app.get_api_key(), "AIzaTestKey456")

    def test_generate_renders_specific_api_error_banner(self):
        with mock.patch.object(
                workout_app, "query_gemini",
                side_effect=workout_app.GeminiError(
                    "invalid_api_key",
                    "API Key Authentication Error",
                    "The Gemini API key is missing or invalid."
                )):
            response = self.client.post("/generate", data=VALID_FORM)

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 503)
        self.assertIn("api-error-box", body)
        self.assertIn("API Key Authentication Error", body)
        self.assertIn("The Gemini API key is missing or invalid.", body)

    def test_healthz(self):
        response = self.client.get("/healthz")
        payload = json.loads(response.get_data(as_text=True))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["gemini_key_configured"])



@unittest.skipUnless(os.getenv("RUN_LIVE_GEMINI_TEST") == "1",
                     "set RUN_LIVE_GEMINI_TEST=1 to call the real Gemini API")
class LiveGeminiTestCase(unittest.TestCase):
    """Tests that hit the real Gemini API (no generation is billed)."""

    def test_live_invalid_api_key_reports_configuration_error(self):
        """A rejected API key must produce a safe 503, not a silent failure."""
        workout_app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        original_key, original_client = workout_app.api_key, workout_app._gemini_client
        workout_app.api_key = "invalid-placeholder-key"
        workout_app._gemini_client = None
        try:
            response = workout_app.app.test_client().post("/generate", data=VALID_FORM)
        finally:
            workout_app.api_key = original_key
            workout_app._gemini_client = original_client

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 503, msg=body[:500])
        self.assertIn("not configured correctly", body)

    def test_live_generate(self):
        workout_app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        client = workout_app.app.test_client()

        response = client.post("/generate", data=VALID_FORM, follow_redirects=True)

        self.assertEqual(response.status_code, 200,
                         msg=response.get_data(as_text=True)[:500])
        body = response.get_data(as_text=True).lower()
        self.assertIn("workout", body)
        self.assertNotIn("unable to generate", body)


if __name__ == "__main__":
    unittest.main()

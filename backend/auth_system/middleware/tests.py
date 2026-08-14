import json
import logging
from django.test import SimpleTestCase, RequestFactory
from unittest.mock import MagicMock
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from auth_system.middleware.api_logger import APILoggerMiddleware, mask_sensitive_data, parse_and_mask_body

User = get_user_model()

class APILoggerMiddlewareTestCase(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_mask_sensitive_data(self):
        data = {
            "username": "john_doe",
            "password": "secret_password123",
            "nested": {
                "token": "bearer_xyz_123",
                "normal_field": "hello"
            }
        }
        masked = mask_sensitive_data(data)
        self.assertEqual(masked["username"], "john_doe")
        self.assertEqual(masked["password"], "***REDACTED***")
        self.assertEqual(masked["nested"]["token"], "***REDACTED***")
        self.assertEqual(masked["nested"]["normal_field"], "hello")

    def test_parse_and_mask_body(self):
        json_bytes = json.dumps({"password": "123", "email": "test@example.com"}).encode("utf-8")
        result = parse_and_mask_body(json_bytes, "application/json")
        self.assertEqual(result["password"], "***REDACTED***")
        self.assertEqual(result["email"], "test@example.com")

    def test_middleware_request_response_and_db_logging(self):
        def dummy_view(request):
            return HttpResponse(json.dumps({"status": "ok", "token": "secret_token"}), content_type="application/json")

        middleware = APILoggerMiddleware(dummy_view)

        request = self.factory.post(
            "/api/test-endpoint/",
            data=json.dumps({"password": "my_secret_password"}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer secret_jwt_token"
        )
        request.COOKIES["sessionid"] = "secret_session_id"

        with self.assertLogs("api_logger", level="INFO") as api_cm:
            response = middleware(request)

        self.assertEqual(response.status_code, 200)

        # Check API log outputs
        api_log_text = "".join(api_cm.output)
        self.assertIn("Method: POST", api_log_text)
        self.assertIn("URL: /api/test-endpoint/", api_log_text)
        self.assertIn("***REDACTED***", api_log_text)
        self.assertNotIn("my_secret_password", api_log_text)
        self.assertNotIn("secret_jwt_token", api_log_text)


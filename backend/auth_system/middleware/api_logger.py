import json
import logging
import time
from typing import Any, Dict
from django.db import connection

api_logger = logging.getLogger("api_logger")
db_logger = logging.getLogger("db_logger")

SENSITIVE_KEYS = {
    "password", "password_confirm", "token", "access", "refresh",
    "secret", "authorization", "key", "credit_card", "card_number", "cvv"
}

def mask_sensitive_data(data: Any) -> Any:
    """Recursively mask sensitive values in dictionaries and lists."""
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if any(sens_key in key.lower() for sens_key in SENSITIVE_KEYS):
                masked[key] = "***REDACTED***"
            else:
                masked[key] = mask_sensitive_data(value)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data

def parse_and_mask_body(body_bytes: bytes, content_type: str = "") -> Any:
    """Parse request/response body bytes, mask sensitive keys, and return formatted representation."""
    if not body_bytes:
        return None

    if "application/json" in content_type.lower() or content_type == "":
        try:
            parsed_json = json.loads(body_bytes.decode("utf-8"))
            return mask_sensitive_data(parsed_json)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    try:
        decoded = body_bytes.decode("utf-8", errors="replace")
        if len(decoded) > 1000:
            return decoded[:1000] + " ... [truncated]"
        return decoded
    except Exception:
        return "[Binary Content]"


class APILoggerMiddleware:
    """
    Middleware that logs:
    - API Request: Method, URL, Headers, Body, Cookies
    - API Response: Status code, Headers, Body, Cookies, Execution Duration
    - DB Queries: SQL statements and timing executed during the request
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.perf_counter()

        # 1. Capture Request Info
        req_method = request.method
        req_url = request.get_full_path()
        req_headers = self._extract_headers(request.META)
        req_cookies = mask_sensitive_data(dict(request.COOKIES))
        
        # Safe body extraction
        content_type = request.META.get("CONTENT_TYPE", "")
        req_body = None
        if "multipart/form-data" not in content_type:
            try:
                req_body = parse_and_mask_body(request.body, content_type)
            except Exception as e:
                req_body = f"[Error reading body: {str(e)}]"
        else:
            req_body = "[Multipart Form Data]"

        # Log Request Before Processing
        api_logger.info(
            f"\n--- [API REQUEST LOG] ---\n"
            f"Method: {req_method}\n"
            f"URL: {req_url}\n"
            f"Headers: {json.dumps(req_headers, indent=2)}\n"
            f"Cookies: {json.dumps(req_cookies, indent=2)}\n"
            f"Body: {json.dumps(req_body, indent=2) if isinstance(req_body, (dict, list)) else req_body}\n"
            f"-------------------------"
        )

        # 2. Intercept DB Queries during Request Execution
        db_queries = []
        
        def db_query_wrapper(execute, sql, params, many, context):
            q_start = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                q_duration = (time.perf_counter() - q_start) * 1000
                query_info = {
                    "sql": sql,
                    "params": str(params),
                    "duration_ms": round(q_duration, 2)
                }
                db_queries.append(query_info)
                db_logger.info(f"[DB SQL] [{query_info['duration_ms']}ms] {sql} | Params: {params}")

        # Execute view under DB execution wrapper
        with connection.execute_wrapper(db_query_wrapper):
            response = self.get_response(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 3. Capture Response Info
        resp_status = response.status_code
        resp_headers = self._extract_response_headers(response)
        resp_cookies = mask_sensitive_data({k: v.value for k, v in response.cookies.items()})
        
        resp_content_type = response.headers.get("Content-Type", "") if hasattr(response, "headers") else response.get("Content-Type", "")
        
        resp_body = None
        if hasattr(response, "streaming") and response.streaming:
            resp_body = "[Streaming Response]"
        elif hasattr(response, "content"):
            resp_body = parse_and_mask_body(response.content, resp_content_type)

        total_db_time = round(sum(q["duration_ms"] for q in db_queries), 2)

        # Log Response After Processing
        api_logger.info(
            f"\n=== [API RESPONSE LOG] ===\n"
            f"Method: {req_method} | URL: {req_url}\n"
            f"Status: {resp_status} | Time: {duration_ms}ms (DB: {total_db_time}ms, Queries: {len(db_queries)})\n"
            f"Headers: {json.dumps(resp_headers, indent=2)}\n"
            f"Cookies: {json.dumps(resp_cookies, indent=2)}\n"
            f"Body: {json.dumps(resp_body, indent=2) if isinstance(resp_body, (dict, list)) else resp_body}\n"
            f"=========================="
        )

        # 4. Save to separate Database ('logs_db') ONLY for target endpoints (e.g. TV Booking)
        TARGET_DB_LOG_ENDPOINTS = ['/api/tv-bookings', '/api/tvbookings', '/tv-bookings']
        if any(target in req_url for target in TARGET_DB_LOG_ENDPOINTS):
            try:
                from camphub.models import APILog
                req_body_str = json.dumps(req_body) if isinstance(req_body, (dict, list)) else (str(req_body) if req_body else "")
                resp_body_str = json.dumps(resp_body) if isinstance(resp_body, (dict, list)) else (str(resp_body) if resp_body else "")
                APILog.objects.using('logs_db').create(
                    endpoint=req_url,
                    method=req_method,
                    status_code=resp_status,
                    request_body=req_body_str,
                    response_body=resp_body_str,
                    execution_time_ms=duration_ms
                )
            except Exception as e:
                api_logger.error(f"[DB Log Error] Failed to save log to logs_db: {str(e)}")

        return response


    def _extract_headers(self, meta: Dict[str, Any]) -> Dict[str, str]:
        """Extract HTTP headers from request.META and mask authorization tokens."""
        headers = {}
        for key, value in meta.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                headers[header_name] = value
            elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                header_name = key.replace("_", "-").title()
                headers[header_name] = value

        # Mask sensitive headers
        if "Authorization" in headers:
            headers["Authorization"] = "***REDACTED***"
        return headers

    def _extract_response_headers(self, response) -> Dict[str, str]:
        """Extract headers from HTTP response object."""
        headers = {}
        if hasattr(response, "headers"):
            for k, v in response.headers.items():
                headers[k] = v
        elif hasattr(response, "_headers"):
            for k, (header_name, val) in response._headers.items():
                headers[header_name] = val
        return headers

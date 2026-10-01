import io
import json
import os
import re
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from guardrails import (
    SlidingWindowRateLimiter,
    InFlightLock,
    rate_limiter,
    in_flight_guard,
    reset_rate_limits,
    reset_in_flight_locks,
)


class TestGuardrails(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

    def setUp(self):
        app.config["TESTING"] = True
        app.config["RATELIMIT_ENABLED"] = False
        app.config["CONCURRENT_LOCK_ENABLED"] = True
        reset_rate_limits()
        reset_in_flight_locks()
        self.client = app.test_client()

    def tearDown(self):
        reset_rate_limits()
        reset_in_flight_locks()
        app.config["RATELIMIT_ENABLED"] = False

    def _get_sample_file(self, filename):
        file_path = os.path.join(self.data_dir, filename)
        with open(file_path, "rb") as f:
            return io.BytesIO(f.read()), filename

    def _build_analyze_payload(self, budget="5000000"):
        sp_orders, sp_o_name = self._get_sample_file("shopee_orders.csv")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")
        return {
            "shopee_orders": (sp_orders, sp_o_name),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": str(budget),
        }

    # =========================================================================
    # 1. Unit Tests: SlidingWindowRateLimiter & InFlightLock
    # =========================================================================

    def test_sliding_window_rate_limiter_unit(self):
        limiter = SlidingWindowRateLimiter()
        ip = "192.168.1.100"
        bucket = "test_bucket"

        # Allow 3 requests in a 10s window
        for i in range(3):
            allowed, retry_after = limiter.check(ip, bucket, limit=3, window=10)
            self.assertTrue(allowed, f"Request {i+1} should be allowed")
            self.assertEqual(retry_after, 0)

        # 4th request must be rejected
        allowed, retry_after = limiter.check(ip, bucket, limit=3, window=10)
        self.assertFalse(allowed, "4th request should be rejected")
        self.assertGreater(retry_after, 0)
        self.assertLessEqual(retry_after, 10)

        # Different IP should have independent quota
        other_ip = "192.168.1.101"
        allowed, _ = limiter.check(other_ip, bucket, limit=3, window=10)
        self.assertTrue(allowed, "Different IP should have independent quota")

        # Different bucket should have independent quota
        allowed, _ = limiter.check(ip, "another_bucket", limit=3, window=10)
        self.assertTrue(allowed, "Different bucket should have independent quota")

        # Reset clears state
        limiter.reset()
        allowed, retry_after = limiter.check(ip, bucket, limit=3, window=10)
        self.assertTrue(allowed, "After reset, request should be allowed again")

    def test_sliding_window_eviction(self):
        limiter = SlidingWindowRateLimiter()
        ip = "10.0.0.1"
        bucket = "window_test"

        t0 = 1000.0
        with patch("guardrails.time.time", return_value=t0):
            allowed, _ = limiter.check(ip, bucket, limit=2, window=5)
            self.assertTrue(allowed)
            allowed, _ = limiter.check(ip, bucket, limit=2, window=5)
            self.assertTrue(allowed)
            allowed, retry = limiter.check(ip, bucket, limit=2, window=5)
            self.assertFalse(allowed)
            self.assertEqual(retry, 5)

        # Advance time by 6 seconds (beyond window)
        with patch("guardrails.time.time", return_value=t0 + 6.0):
            allowed, retry = limiter.check(ip, bucket, limit=2, window=5)
            self.assertTrue(allowed, "Should be allowed after window passes")
            self.assertEqual(retry, 0)

    def test_in_flight_lock_unit(self):
        lock = InFlightLock()
        ip = "192.168.1.50"
        endpoint = "analyze"

        # First acquire succeeds
        self.assertTrue(lock.acquire(ip, endpoint))

        # Concurrent acquire on same key fails
        self.assertFalse(lock.acquire(ip, endpoint))

        # Different endpoint succeeds
        self.assertTrue(lock.acquire(ip, "cogs_upload"))

        # Release frees the key
        lock.release(ip, endpoint)
        self.assertTrue(lock.acquire(ip, endpoint))

        # Reset clears all
        lock.reset()
        self.assertTrue(lock.acquire(ip, endpoint))

    # =========================================================================
    # 2. Integration Tests: Rate Limiting & HTTP 429 Feedback
    # =========================================================================

    def test_api_rate_limit_analyze_10_requests(self):
        app.config["RATELIMIT_ENABLED"] = True
        reset_rate_limits()

        # Seed COGS first while rate limit disabled to save quota
        app.config["RATELIMIT_ENABLED"] = False
        f_bytes, name = self._get_sample_file("internal_cogs_hpp.csv")
        self.client.post("/api/cogs/upload", data={"cogs_file": (f_bytes, name)}, content_type="multipart/form-data")
        app.config["RATELIMIT_ENABLED"] = True

        # Send 10 valid requests
        for i in range(10):
            payload = self._build_analyze_payload()
            res = self.client.post("/api/analyze", data=payload, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200, f"Request {i+1} should succeed with 200")

        # 11th request must return 429 Too Many Requests
        payload = self._build_analyze_payload()
        res = self.client.post("/api/analyze", data=payload, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 429)

        # Verify Retry-After header and JSON body
        self.assertIn("Retry-After", res.headers)
        body = res.get_json()
        self.assertIn("error", body)
        self.assertIn("retry_after", body)
        self.assertIn("Terlalu banyak permintaan", body["error"])
        self.assertGreater(int(res.headers["Retry-After"]), 0)

    def test_api_rate_limit_cogs_upload_10_requests(self):
        app.config["RATELIMIT_ENABLED"] = True
        reset_rate_limits()

        for i in range(10):
            f_bytes, name = self._get_sample_file("internal_cogs_hpp.csv")
            res = self.client.post("/api/cogs/upload", data={"cogs_file": (f_bytes, name)}, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200, f"Request {i+1} should succeed with 200")

        # 11th request rejected
        f_bytes, name = self._get_sample_file("internal_cogs_hpp.csv")
        res = self.client.post("/api/cogs/upload", data={"cogs_file": (f_bytes, name)}, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 429)
        body = res.get_json()
        self.assertIn("retry_after", body)

    def test_api_rate_limit_sample_data_20_requests(self):
        app.config["RATELIMIT_ENABLED"] = True
        reset_rate_limits()

        for i in range(20):
            res = self.client.get("/api/sample-data")
            self.assertEqual(res.status_code, 200, f"Request {i+1} should succeed")

        # 21st request rejected
        res = self.client.get("/api/sample-data")
        self.assertEqual(res.status_code, 429)
        self.assertIn("Retry-After", res.headers)

    # =========================================================================
    # 3. Concurrent In-Flight Request Mutex Guard
    # =========================================================================

    def test_concurrent_request_lock_blocks_duplicate(self):
        app.config["RATELIMIT_ENABLED"] = False
        app.config["CONCURRENT_LOCK_ENABLED"] = True
        reset_in_flight_locks()

        # Manually acquire the lock for 127.0.0.1 on analyze endpoint
        in_flight_guard.acquire("127.0.0.1", "analyze")

        try:
            # Attempt a request while lock is held
            payload = self._build_analyze_payload()
            res = self.client.post("/api/analyze", data=payload, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 429)
            body = res.get_json()
            self.assertIn("Permintaan analisis sebelumnya sedang diproses", body.get("error", ""))
        finally:
            in_flight_guard.release("127.0.0.1", "analyze")

        # Once released, request should succeed
        payload = self._build_analyze_payload()
        res = self.client.post("/api/analyze", data=payload, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)

    # =========================================================================
    # 4. Payload Size Limit Guard (HTTP 413)
    # =========================================================================

    def test_payload_too_large_413(self):
        # Create dummy file > 16 MB (e.g. 17 MB)
        oversized_data = b"X" * (17 * 1024 * 1024)
        data = {
            "shopee_orders": (io.BytesIO(oversized_data), "huge_orders.csv"),
            "tiktok_orders": (io.BytesIO(b"id,sku\n1,s1"), "tt.csv"),
            "shopee_inventory": (io.BytesIO(b"sku,stock\ns1,10"), "sp_inv.csv"),
            "tiktok_inventory": (io.BytesIO(b"sku,stock\ns1,10"), "tt_inv.csv"),
            "campaign_budget": "5000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 413)
        body = res.get_json()
        self.assertIn("error", body)
        self.assertIn("16 MB", body["error"])

    # =========================================================================
    # 5. Campaign Budget Bounds Guard
    # =========================================================================

    def test_campaign_budget_bounds_negative(self):
        payload = self._build_analyze_payload(budget="-1000")
        res = self.client.post("/api/analyze", data=payload, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("tidak boleh negatif", res.get_json().get("error", ""))

    def test_campaign_budget_bounds_exceeded(self):
        # Exceeds 1 trillion (1.000.000.000.000)
        payload = self._build_analyze_payload(budget="1000000000001")
        res = self.client.post("/api/analyze", data=payload, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("melebihi batas maksimal", res.get_json().get("error", ""))

    def test_campaign_budget_bounds_valid(self):
        # 0 is valid
        payload = self._build_analyze_payload(budget="0")
        res = self.client.post("/api/analyze", data=payload, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)

        # 1 trillion is valid
        payload = self._build_analyze_payload(budget="1000000000000")
        res = self.client.post("/api/analyze", data=payload, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)

    # =========================================================================
    # 6. Tabular Max Row Limit Guard (50,000 rows)
    # =========================================================================

    def test_max_row_limit_enforced(self):
        header = "order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
        # 50,001 data rows
        row = "ORD1,2026-10-10 00:01:00,COMPLETED,SKU-TEST,Item,1,10000,9000\n"
        huge_csv = (header + row * 50005).encode("utf-8")

        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

        data = {
            "shopee_orders": (io.BytesIO(huge_csv), "shopee_orders.csv"),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": "5000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        self.assertIn("batas maksimal 50000 baris", res.get_json().get("error", ""))

    # =========================================================================
    # 7. Client-Side Code & Resilience Contracts Inspection
    # =========================================================================

    def test_client_guardrails_contracts_in_app_js(self):
        js_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "app.js"))
        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()

        # In-flight lock & debouncing flag
        self.assertIn("isAnalyzing", js_content, "static/app.js must maintain isAnalyzing flag")
        self.assertIn("is-loading", js_content, "static/app.js must apply .is-loading class")

        # AbortController with 30s timeout
        self.assertIn("AbortController", js_content, "static/app.js must utilize AbortController")
        self.assertIn("30000", js_content, "static/app.js must have 30000ms (30s) timeout limit")

        # Pre-flight file size check (10MB per file, 16MB total)
        self.assertIn("10 * 1024 * 1024", js_content, "static/app.js must check 10 MB per file")
        self.assertIn("16 * 1024 * 1024", js_content, "static/app.js must check 16 MB total file limit")

        # Offline & network disconnection listeners
        self.assertIn("offline", js_content, "static/app.js must handle offline event")
        self.assertIn("online", js_content, "static/app.js must handle online event")

        # 429 countdown feedback
        self.assertIn("429", js_content, "static/app.js must handle HTTP 429 response")
        self.assertIn("Retry-After", js_content, "static/app.js must read Retry-After header")

        # No Emoji Policy check on app.js
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F"
            r"\U0001F300-\U0001F5FF"
            r"\U0001F680-\U0001F6FF"
            r"\U0001F1E0-\U0001F1FF"
            r"\U00002702-\U000027B0"
            r"\U000024C2-\U0001F251"
            r"\U0001F900-\U0001F9FF"
            r"\U0001FA70-\U0001FAFF"
            r"\U00002600-\U000026FF]"
        )
        self.assertIsNone(emoji_pattern.search(js_content), "No emoji characters allowed in static/app.js")

    def test_style_css_is_loading_present(self):
        css_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "style.css"))
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        self.assertIn(".is-loading", css_content, "static/style.css must define styles for .is-loading")


if __name__ == "__main__":
    unittest.main()

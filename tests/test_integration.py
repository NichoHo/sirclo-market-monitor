import io
import os
import unittest

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app import app
except ImportError:
    app = None


class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

    def setUp(self):
        if app is None:
            self.skipTest("Flask app not available")
        app.config["TESTING"] = True
        self.client = app.test_client()

    def _get_file(self, filename):
        path = os.path.join(self.data_dir, filename)
        with open(path, "rb") as f:
            return io.BytesIO(f.read()), filename

    def test_integration_full_pipeline(self):
        # Step 1: Upload COGS
        cogs_io, cogs_name = self._get_file("internal_cogs_hpp.csv")
        cogs_res = self.client.post("/api/cogs/upload", data={"cogs_file": (cogs_io, cogs_name)}, content_type="multipart/form-data")
        self.assertEqual(cogs_res.status_code, 200)

        # Step 2: Upload 4 marketplace CSVs
        sp_orders, sp_o_name = self._get_file("shopee_orders.csv")
        tt_orders, tt_o_name = self._get_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_file("tiktok_inventory.csv")

        data = {
            "shopee_orders": (sp_orders, sp_o_name),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": "5000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()

        # Verify all 5 sections present
        self.assertTrue(len(body["margin_alerts"]) > 0)
        self.assertIsNotNone(body["budget_status"])
        self.assertTrue(len(body["run_rate"]) > 0)
        self.assertTrue(len(body["rebalance"]) > 0)
        self.assertTrue(body["summary_text"].startswith("RINGKASAN MARKETPLACE MONITOR"))

    def test_integration_cogs_persistence(self):
        cogs_io, cogs_name = self._get_file("internal_cogs_hpp.csv")
        self.client.post("/api/cogs/upload", data={"cogs_file": (cogs_io, cogs_name)}, content_type="multipart/form-data")

        # Create fresh test client to simulate separate request cycle
        fresh_client = app.test_client()
        res = fresh_client.get("/api/cogs")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["count"], 50)

    def test_integration_sample_data_counts(self):
        res = self.client.get("/api/sample-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        negatives = [a for a in body["margin_alerts"] if a["level"] == "negative"]
        # Expect at least 15 negative margin items (simulation has 9 on Shopee + 8 on TikTok)
        self.assertTrue(len(negatives) >= 15)


if __name__ == "__main__":
    unittest.main()

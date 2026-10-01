import io
import json
import os
import unittest

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app import app
except ImportError:
    app = None


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

    def setUp(self):
        if app is None:
            self.skipTest("Flask app not available")
        app.config["TESTING"] = True
        self.client = app.test_client()

    def _get_sample_file(self, filename):
        file_path = os.path.join(self.data_dir, filename)
        with open(file_path, "rb") as f:
            return io.BytesIO(f.read()), filename

    def _seed_cogs(self):
        f_bytes, name = self._get_sample_file("internal_cogs_hpp.csv")
        data = {"cogs_file": (f_bytes, name)}
        res = self.client.post("/api/cogs/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)

    def test_api_cogs_upload(self):
        f_bytes, name = self._get_sample_file("internal_cogs_hpp.csv")
        data = {"cogs_file": (f_bytes, name)}
        res = self.client.post("/api/cogs/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body.get("inserted"), 50)

        get_res = self.client.get("/api/cogs")
        self.assertEqual(get_res.status_code, 200)
        get_body = get_res.get_json()
        self.assertEqual(get_body.get("count"), 50)

    def test_api_cogs_get(self):
        self._seed_cogs()
        res = self.client.get("/api/cogs")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertIn("data", body)
        self.assertIn("count", body)
        self.assertTrue(len(body["data"]) >= 50)

    def test_api_cogs_update(self):
        self._seed_cogs()
        res = self.client.put(
            "/api/cogs/SKU-SUNSCREEN-01",
            data=json.dumps({"hpp_per_unit": 70000}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body.get("sku"), "SKU-SUNSCREEN-01")
        self.assertEqual(body.get("hpp_per_unit"), 70000)

    def test_api_cogs_update_not_found(self):
        res = self.client.put(
            "/api/cogs/SKU-NONEXISTENT",
            data=json.dumps({"hpp_per_unit": 50000}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404)

    def test_api_cogs_delete(self):
        self._seed_cogs()
        initial_get = self.client.get("/api/cogs").get_json()
        initial_count = initial_get["count"]

        del_res = self.client.delete("/api/cogs/SKU-SUNSCREEN-01")
        self.assertEqual(del_res.status_code, 200)

        after_get = self.client.get("/api/cogs").get_json()
        self.assertEqual(after_get["count"], initial_count - 1)

    def test_api_analyze_full(self):
        self._seed_cogs()
        sp_orders, sp_o_name = self._get_sample_file("shopee_orders.csv")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

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
        expected_keys = {"margin_alerts", "budget_status", "run_rate", "rebalance", "unmapped_skus", "warnings", "summary_text"}
        self.assertTrue(expected_keys.issubset(body.keys()))

    def test_api_analyze_negative_margins(self):
        self._seed_cogs()
        sp_orders, sp_o_name = self._get_sample_file("shopee_orders.csv")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

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
        negative_alerts = [a for a in body["margin_alerts"] if a["level"] == "negative"]
        self.assertTrue(len(negative_alerts) >= 15)

    def test_api_analyze_budget_status(self):
        self._seed_cogs()
        sp_orders, sp_o_name = self._get_sample_file("shopee_orders.csv")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

        data = {
            "shopee_orders": (sp_orders, sp_o_name),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": "5000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        status = res.get_json()["budget_status"]
        for field in ["total_loss", "campaign_budget", "remaining", "pct_used", "meter_level"]:
            self.assertIn(field, status)

    def test_api_analyze_run_rate(self):
        self._seed_cogs()
        sp_orders, sp_o_name = self._get_sample_file("shopee_orders.csv")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

        data = {
            "shopee_orders": (sp_orders, sp_o_name),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": "5000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        run_rate = res.get_json()["run_rate"]
        self.assertTrue(len(run_rate) > 0)
        first = run_rate[0]
        self.assertIn("run_rate_per_hour", first)
        self.assertIn("hours_until_stockout", first)
        self.assertIn("stockout_time", first)

    def test_api_analyze_rebalance(self):
        self._seed_cogs()
        sp_orders, sp_o_name = self._get_sample_file("shopee_orders.csv")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

        data = {
            "shopee_orders": (sp_orders, sp_o_name),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": "5000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        rebalance = res.get_json()["rebalance"]
        self.assertTrue(len(rebalance) > 0)
        for r in rebalance:
            self.assertTrue(r["shopee_stock"] <= 5 or r["tiktok_stock"] <= 5)
            self.assertTrue(r["warehouse_stock"] > 50)

    def test_api_analyze_missing_file(self):
        sp_orders, sp_o_name = self._get_sample_file("shopee_orders.csv")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")

        data = {
            "shopee_orders": (sp_orders, sp_o_name),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "campaign_budget": "5000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)

    def test_api_analyze_bad_csv(self):
        self._seed_cogs()
        bad_orders = io.BytesIO(b"bad_column_1,bad_column_2\n1,2\n")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

        data = {
            "shopee_orders": (bad_orders, "shopee_bad.csv"),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": "5000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        err = res.get_json().get("error", "")
        self.assertTrue(len(err) > 0)

    def test_api_analyze_summary_text(self):
        self._seed_cogs()
        sp_orders, sp_o_name = self._get_sample_file("shopee_orders.csv")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

        data = {
            "shopee_orders": (sp_orders, sp_o_name),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": "5000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        summary = res.get_json().get("summary_text", "")
        self.assertTrue(summary.startswith("RINGKASAN MARKETPLACE MONITOR"))

    def test_api_sample_data(self):
        res = self.client.get("/api/sample-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        expected_keys = {"margin_alerts", "budget_status", "run_rate", "rebalance", "unmapped_skus", "warnings", "summary_text"}
        self.assertTrue(expected_keys.issubset(body.keys()))

    def test_frontend_empty_state(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Muat Data Sample 10.10", html)

    def test_api_cogs_upload_missing_file(self):
        res = self.client.post("/api/cogs/upload", data={}, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)

    def test_api_cogs_upload_invalid_csv(self):
        bad_csv = io.BytesIO(b"wrong_header_1,wrong_header_2\n1,2\n")
        data = {"cogs_file": (bad_csv, "bad.csv")}
        res = self.client.post("/api/cogs/upload", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)

    def test_api_cogs_update_invalid_body(self):
        res = self.client.put(
            "/api/cogs/SKU-SUNSCREEN-01",
            data=json.dumps({"hpp_per_unit": "not-a-number"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_api_analyze_unmapped_skus(self):
        self._seed_cogs()
        unmapped_orders = (
            b"order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
            b"ORD999,2026-10-10 00:01:00,Completed,SKU-UNKNOWN-ITEM,Unknown Item,1,100000,50000\n"
        )
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

        data = {
            "shopee_orders": (io.BytesIO(unmapped_orders), "sp_orders.csv"),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": "5000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        unmapped = res.get_json().get("unmapped_skus", [])
        self.assertIn("SKU-UNKNOWN-ITEM", unmapped)

    def test_api_analyze_invalid_budget(self):
        self._seed_cogs()
        sp_orders, sp_o_name = self._get_sample_file("shopee_orders.csv")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

        data = {
            "shopee_orders": (sp_orders, sp_o_name),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": "invalid_budget_number",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)

    def test_api_analyze_zero_budget(self):
        self._seed_cogs()
        sp_orders, sp_o_name = self._get_sample_file("shopee_orders.csv")
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

        data = {
            "shopee_orders": (sp_orders, sp_o_name),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": "0",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        budget = res.get_json()["budget_status"]
        self.assertEqual(budget["meter_level"], "safe")

    def test_api_analyze_empty_csvs(self):
        self._seed_cogs()
        sp_header = b"order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
        tt_header = b"order_id,created_time,order_status,seller_sku,product_name,quantity,retail_price,net_unit_settlement_price\n"
        sp_inv_h = b"sku_reference_no,product_name,current_stock\n"
        tt_inv_h = b"seller_sku,product_name,available_stock\n"

        data = {
            "shopee_orders": (io.BytesIO(sp_header), "sp_orders.csv"),
            "tiktok_orders": (io.BytesIO(tt_header), "tt_orders.csv"),
            "shopee_inventory": (io.BytesIO(sp_inv_h), "sp_inv.csv"),
            "tiktok_inventory": (io.BytesIO(tt_inv_h), "tt_inv.csv"),
            "campaign_budget": "1000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["margin_alerts"], [])

    def test_api_analyze_warnings_returned(self):
        self._seed_cogs()
        csv_with_bad_row = (
            b"order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
            b"ORD01,2026-10-10 00:01:00,Completed,SKU-SUNSCREEN-01,Sunscreen,bad_qty,100000,90000\n"
        )
        tt_orders, tt_o_name = self._get_sample_file("tiktok_orders.csv")
        sp_inv, sp_i_name = self._get_sample_file("shopee_inventory.csv")
        tt_inv, tt_i_name = self._get_sample_file("tiktok_inventory.csv")

        data = {
            "shopee_orders": (io.BytesIO(csv_with_bad_row), "sp_orders.csv"),
            "tiktok_orders": (tt_orders, tt_o_name),
            "shopee_inventory": (sp_inv, sp_i_name),
            "tiktok_inventory": (tt_inv, tt_i_name),
            "campaign_budget": "5000000",
        }
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        warnings = res.get_json().get("warnings", [])
        self.assertTrue(len(warnings) > 0)


if __name__ == "__main__":
    unittest.main()

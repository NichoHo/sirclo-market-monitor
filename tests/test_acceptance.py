from datetime import datetime, timedelta
import io
import math
import os
import time
import unittest

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from app import app
    from engine import calculate_margins, calculate_budget, calculate_run_rate, calculate_rebalance
    from summary import generate_summary_text, generate_alert_copy_text
except ImportError:
    app = None


class TestAcceptanceCriteria(unittest.TestCase):
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

    # AC 1: Upload 4 CSV + klik Analisis -> hasil muncul dalam < 30 detik
    def test_ac1_analysis_speed(self):
        cogs_io, cogs_name = self._get_file("internal_cogs_hpp.csv")
        self.client.post("/api/cogs/upload", data={"cogs_file": (cogs_io, cogs_name)}, content_type="multipart/form-data")

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

        start_time = time.time()
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        elapsed = time.time() - start_time

        self.assertEqual(res.status_code, 200)
        self.assertLess(elapsed, 30.0, f"Analysis took {elapsed}s, expected < 30s")

    # AC 2: Semua order dengan harga jual aktual < HPP terdeteksi dan muncul di tab Jual Rugi
    def test_ac2_all_negative_margins_detected(self):
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-LOSS-1", "product_name": "P1", "qty": 1, "original_price": 100000, "actual_unit_price": 40000, "channel": "shopee"},
            {"order_id": "O2", "created_at": "2026-10-10 00:00:00", "sku": "SKU-PROFIT", "product_name": "P2", "qty": 1, "original_price": 100000, "actual_unit_price": 80000, "channel": "shopee"},
            {"order_id": "O3", "created_at": "2026-10-10 00:00:00", "sku": "SKU-LOSS-2", "product_name": "P3", "qty": 1, "original_price": 100000, "actual_unit_price": 30000, "channel": "tiktok"},
        ]
        cogs = {"SKU-LOSS-1": 50000, "SKU-PROFIT": 50000, "SKU-LOSS-2": 50000}
        alerts, _ = calculate_margins(orders, cogs)

        negative_skus = {a["sku"] for a in alerts if a["level"] == "negative"}
        self.assertEqual(negative_skus, {"SKU-LOSS-1", "SKU-LOSS-2"})

    # AC 3: Run rate = total terjual ÷ jam berjalan — akurat vs hitung manual
    def test_ac3_run_rate_accuracy(self):
        now = datetime(2026, 10, 10, 3, 0, 0)
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-RUN", "product_name": "P1", "qty": 15, "channel": "shopee"}
        ]
        inventory = [{"sku": "SKU-RUN", "product_name": "P1", "channel_stock": 100, "channel": "shopee"}]

        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        self.assertEqual(len(run_rates), 1)
        expected_rate = 15 / 3.0  # 5.0
        self.assertAlmostEqual(run_rates[0]["run_rate_per_hour"], expected_rate, places=2)

    # AC 4: Prediksi habis = stok sisa ÷ run rate — toleransi ± 15 menit
    def test_ac4_stockout_prediction_tolerance(self):
        now = datetime(2026, 10, 10, 2, 0, 0)
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-STK", "product_name": "P1", "qty": 10, "channel": "shopee"} # rate = 5/hr
        ]
        inventory = [{"sku": "SKU-STK", "product_name": "P1", "channel_stock": 25, "channel": "shopee"}]

        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        expected_hours = 25 / 5.0  # 5.0 hours
        actual_hours = run_rates[0]["hours_until_stockout"]

        # 15 minutes is 0.25 hours
        self.assertAlmostEqual(actual_hours, expected_hours, delta=0.25)

    # AC 5: Budget meter = sum seluruh kerugian order yang jual di bawah HPP
    def test_ac5_budget_meter_sum(self):
        alerts = [
            {"order_id": "O1", "sku": "S1", "margin": -10000, "level": "negative", "qty": 2}, # 20,000 loss
            {"order_id": "O2", "sku": "S2", "margin": -15000, "level": "negative", "qty": 3}, # 45,000 loss
            {"order_id": "O3", "sku": "S3", "margin": 5000, "level": "warning", "qty": 1},   # profitable
        ]
        budget = calculate_budget(alerts, campaign_budget=1000000)
        self.assertEqual(budget["total_loss"], 65000)

    # AC 6: SKU dengan stok marketplace ≤ 5 dan warehouse > 50 muncul di tab Rebalancing
    def test_ac6_rebalancing_starved_skus(self):
        inventory = [
            {"sku": "SKU-HERO-01", "product_name": "Hero 1", "channel_stock": 0, "channel": "shopee"},
            {"sku": "SKU-HERO-01", "product_name": "Hero 1", "channel_stock": 25, "channel": "tiktok"},
        ]
        warehouse = {"SKU-HERO-01": 500}
        rebalance = calculate_rebalance(inventory, warehouse)

        self.assertEqual(len(rebalance), 1)
        self.assertEqual(rebalance[0]["sku"], "SKU-HERO-01")
        self.assertIn("Replenish Shopee", rebalance[0]["recommendations"][0])

    # AC 7: Klik alert card → clipboard berisi pesan aksi yang sesuai
    def test_ac7_alert_card_copy_format(self):
        alert = {
            "order_id": "261010SP0007",
            "sku": "SKU-LIP-GLAZE-01",
            "product_name": "Dewy Tint Lip Glaze - Nude Peach",
            "channel": "shopee",
            "original_price": 115000,
            "actual_unit_price": 35497,
            "hpp": 55000,
            "margin": -19503,
            "level": "negative",
        }
        text = generate_alert_copy_text(alert)
        self.assertTrue(text.startswith("ALERT:"))
        self.assertIn("SKU-LIP-GLAZE-01", text)
        self.assertIn("-19503", text)
        self.assertIn("shopee", text)
        self.assertIn("Rp 35497", text)
        self.assertIn("Rp 55000", text)
        self.assertIn("Segera cek voucher", text)

    # AC 8: "Salin Ringkasan" → clipboard berisi summary text lengkap
    def test_ac8_summary_text_complete(self):
        budget_status = {"total_loss": 3250000, "campaign_budget": 5000000, "remaining": 1750000, "pct_used": 65.0, "meter_level": "caution"}
        alerts = [{"sku": "SKU-A", "channel": "shopee", "margin": -10000, "level": "negative"}]
        run_rates = [{"sku": "SKU-B", "channel": "tiktok", "stockout_time": "10 Okt 02:30", "hours_until_stockout": 1.5, "level": "negative"}]
        rebalance = [{"sku": "SKU-C", "warehouse_stock": 500, "shopee_stock": 0, "tiktok_stock": 30, "recommendations": ["Replenish Shopee (+100 unit)"]}]

        summary = generate_summary_text(alerts, budget_status, run_rates, rebalance, campaign_name="10.10 Midnight Mega Sale")

        self.assertIn("RINGKASAN MARKETPLACE MONITOR", summary)
        self.assertIn("BUDGET:", summary)
        self.assertIn("ALERT JUAL RUGI", summary)
        self.assertIn("PREDIKSI HABIS", summary)
        self.assertIn("PERLU REPLENISH", summary)

    # AC 9: Data HPP persist setelah upload pertama — tidak hilang saat refresh
    def test_ac9_cogs_persistence(self):
        cogs_io, cogs_name = self._get_file("internal_cogs_hpp.csv")
        self.client.post("/api/cogs/upload", data={"cogs_file": (cogs_io, cogs_name)}, content_type="multipart/form-data")

        # Second request simulates page reload
        res = self.client.get("/api/cogs")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["count"], 50)

    # AC 10: Tombol "Muat Data Sample" berfungsi tanpa upload file
    def test_ac10_sample_data_demo(self):
        res = self.client.get("/api/sample-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertIn("margin_alerts", body)
        self.assertIn("budget_status", body)
        self.assertIn("run_rate", body)
        self.assertIn("rebalance", body)

    # AC 11: SKU tanpa penjualan (velocity = 0) → prediksi habis = "∞", bukan error
    def test_ac11_zero_velocity_infinity(self):
        now = datetime(2026, 10, 10, 2, 0, 0)
        orders = [{"order_id": "O1", "created_at": "2026-10-10 02:00:00", "sku": "SKU-ZERO", "product_name": "P1", "qty": 0, "channel": "shopee"}]
        inventory = [{"sku": "SKU-ZERO", "product_name": "P1", "channel_stock": 50, "channel": "shopee"}]

        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        self.assertEqual(len(run_rates), 1)
        self.assertEqual(run_rates[0]["hours_until_stockout"], float("inf"))
        self.assertIsNone(run_rates[0]["stockout_time"])


if __name__ == "__main__":
    unittest.main()

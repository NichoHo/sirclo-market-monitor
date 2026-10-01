import os
import unittest

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from summary import generate_summary_text, generate_alert_copy_text
except ImportError:
    pass


class TestSummary(unittest.TestCase):
    def test_generate_summary_text_structure(self):
        margin_alerts = [
            {"order_id": "O1", "sku": "SKU-LIP-01", "product_name": "Lipstick", "channel": "shopee", "margin": -15000, "level": "negative", "qty": 1, "actual_unit_price": 50000, "hpp": 65000}
        ]
        budget_status = {
            "total_loss": 15000,
            "campaign_budget": 1000000,
            "remaining": 985000,
            "pct_used": 1.5,
            "meter_level": "safe",
        }
        run_rate = [
            {"sku": "SKU-LIP-01", "product_name": "Lipstick", "channel": "shopee", "total_sold": 10, "hours_elapsed": 2.0, "run_rate_per_hour": 5.0, "channel_stock": 5, "hours_until_stockout": 1.0, "stockout_time": "10 Okt 03:00", "level": "negative"}
        ]
        rebalance = [
            {"sku": "SKU-LIP-01", "product_name": "Lipstick", "warehouse_stock": 500, "shopee_stock": 0, "tiktok_stock": 30, "level": "warning", "recommendations": ["Replenish Shopee (+100 unit)"]}
        ]

        text = generate_summary_text(margin_alerts, budget_status, run_rate, rebalance, campaign_name="10.10 Midnight Mega Sale")

        self.assertIn("RINGKASAN MARKETPLACE MONITOR", text)
        self.assertIn("10.10 Midnight Mega Sale", text)
        self.assertIn("BUDGET:", text)
        self.assertIn("ALERT JUAL RUGI (1 order)", text)
        self.assertIn("PREDIKSI HABIS (1 SKU kritis)", text)
        self.assertIn("PERLU REPLENISH (1 SKU)", text)
        self.assertIn("SKU-LIP-01", text)

    def test_summary_text_rupiah_formatting(self):
        budget_status = {
            "total_loss": 3250000,
            "campaign_budget": 5000000,
            "remaining": 1750000,
            "pct_used": 65.0,
            "meter_level": "caution",
        }
        text = generate_summary_text([], budget_status, [], [], campaign_name="Test Campaign")
        self.assertIn("Rp 3.250.000", text)
        self.assertIn("Rp 5.000.000", text)
        self.assertIn("65", text)

    def test_summary_text_empty_alerts(self):
        budget_status = {
            "total_loss": 0,
            "campaign_budget": 5000000,
            "remaining": 5000000,
            "pct_used": 0.0,
            "meter_level": "safe",
        }
        text = generate_summary_text([], budget_status, [], [])
        self.assertIn("RINGKASAN MARKETPLACE MONITOR", text)
        self.assertIn("Rp 0", text)
        self.assertIn("ALERT JUAL RUGI (0 order)", text)
        self.assertIn("PREDIKSI HABIS (0 SKU kritis)", text)
        self.assertIn("PERLU REPLENISH (0 SKU)", text)

    def test_generate_alert_card_copy_text(self):
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
        copy_text = generate_alert_copy_text(alert)
        expected = "ALERT: SKU-LIP-GLAZE-01 (Dewy Tint Lip Glaze - Nude Peach) jual rugi -19503/unit di shopee. Harga jual Rp 35497, HPP Rp 55000. Segera cek voucher."
        self.assertEqual(copy_text, expected)


if __name__ == "__main__":
    unittest.main()

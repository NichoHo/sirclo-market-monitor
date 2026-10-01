from datetime import datetime, timedelta
import math
import os
import unittest

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from engine import (
        calculate_margins,
        calculate_budget,
        calculate_run_rate,
        calculate_rebalance,
    )
except ImportError:
    pass


class TestEngine(unittest.TestCase):
    def test_margin_positive(self):
        orders = [
            {"order_id": "ORD01", "created_at": "2026-10-10 00:00:00", "sku": "SKU-01", "product_name": "P1", "qty": 1, "original_price": 100000, "actual_unit_price": 75000, "channel": "shopee"}
        ]
        cogs = {"SKU-01": 50000}
        alerts, unmapped = calculate_margins(orders, cogs)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["level"], "positive")
        self.assertEqual(alerts[0]["margin"], 25000)

    def test_margin_warning(self):
        orders = [
            {"order_id": "ORD01", "created_at": "2026-10-10 00:00:00", "sku": "SKU-01", "product_name": "P1", "qty": 1, "original_price": 100000, "actual_unit_price": 55000, "channel": "shopee"}
        ]
        cogs = {"SKU-01": 50000}
        alerts, unmapped = calculate_margins(orders, cogs)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["level"], "warning")
        self.assertEqual(alerts[0]["margin"], 5000)

    def test_margin_negative(self):
        orders = [
            {"order_id": "ORD01", "created_at": "2026-10-10 00:00:00", "sku": "SKU-01", "product_name": "P1", "qty": 1, "original_price": 100000, "actual_unit_price": 40000, "channel": "shopee"}
        ]
        cogs = {"SKU-01": 50000}
        alerts, unmapped = calculate_margins(orders, cogs)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["level"], "negative")
        self.assertEqual(alerts[0]["margin"], -10000)

    def test_margin_sort_order(self):
        orders = [
            {"order_id": "ORD-POS", "created_at": "2026-10-10 00:00:00", "sku": "SKU-POS", "product_name": "P1", "qty": 1, "original_price": 100000, "actual_unit_price": 80000, "channel": "shopee"},
            {"order_id": "ORD-NEG-SMALL", "created_at": "2026-10-10 00:00:00", "sku": "SKU-NEG1", "product_name": "P2", "qty": 1, "original_price": 100000, "actual_unit_price": 45000, "channel": "shopee"},
            {"order_id": "ORD-NEG-BIG", "created_at": "2026-10-10 00:00:00", "sku": "SKU-NEG2", "product_name": "P3", "qty": 1, "original_price": 100000, "actual_unit_price": 30000, "channel": "shopee"},
            {"order_id": "ORD-WARN", "created_at": "2026-10-10 00:00:00", "sku": "SKU-WARN", "product_name": "P4", "qty": 1, "original_price": 100000, "actual_unit_price": 55000, "channel": "shopee"},
        ]
        cogs = {"SKU-POS": 50000, "SKU-NEG1": 50000, "SKU-NEG2": 50000, "SKU-WARN": 50000}
        alerts, unmapped = calculate_margins(orders, cogs)

        self.assertEqual(alerts[0]["order_id"], "ORD-NEG-BIG")   # loss -20000
        self.assertEqual(alerts[1]["order_id"], "ORD-NEG-SMALL") # loss -5000
        self.assertEqual(alerts[0]["level"], "negative")
        self.assertEqual(alerts[1]["level"], "negative")

    def test_margin_unmapped_sku(self):
        orders = [
            {"order_id": "ORD01", "created_at": "2026-10-10 00:00:00", "sku": "SKU-KNOWN", "product_name": "P1", "qty": 1, "original_price": 100000, "actual_unit_price": 70000, "channel": "shopee"},
            {"order_id": "ORD02", "created_at": "2026-10-10 00:00:00", "sku": "SKU-UNKNOWN", "product_name": "P2", "qty": 1, "original_price": 100000, "actual_unit_price": 70000, "channel": "shopee"},
        ]
        cogs = {"SKU-KNOWN": 50000}
        alerts, unmapped = calculate_margins(orders, cogs)
        self.assertEqual(len(alerts), 1)
        self.assertIn("SKU-UNKNOWN", unmapped)

    def test_budget_safe(self):
        alerts = [
            {"order_id": "O1", "sku": "S1", "margin": -10000, "level": "negative", "qty": 10} # 100,000 loss
        ]
        budget_status = calculate_budget(alerts, campaign_budget=1000000) # 10%
        self.assertEqual(budget_status["meter_level"], "safe")
        self.assertAlmostEqual(budget_status["pct_used"], 10.0, places=1)
        self.assertEqual(budget_status["total_loss"], 100000)
        self.assertEqual(budget_status["remaining"], 900000)

    def test_budget_caution(self):
        alerts = [
            {"order_id": "O1", "sku": "S1", "margin": -10000, "level": "negative", "qty": 70} # 700,000 loss
        ]
        budget_status = calculate_budget(alerts, campaign_budget=1000000) # 70%
        self.assertEqual(budget_status["meter_level"], "caution")
        self.assertAlmostEqual(budget_status["pct_used"], 70.0, places=1)

    def test_budget_over(self):
        alerts = [
            {"order_id": "O1", "sku": "S1", "margin": -10000, "level": "negative", "qty": 90} # 900,000 loss
        ]
        budget_status = calculate_budget(alerts, campaign_budget=1000000) # 90%
        self.assertEqual(budget_status["meter_level"], "over")
        self.assertAlmostEqual(budget_status["pct_used"], 90.0, places=1)

    def test_budget_zero_division(self):
        alerts = [
            {"order_id": "O1", "sku": "S1", "margin": -10000, "level": "negative", "qty": 5}
        ]
        budget_status = calculate_budget(alerts, campaign_budget=0)
        self.assertEqual(budget_status["meter_level"], "safe")
        self.assertEqual(budget_status["pct_used"], 0.0)

    def test_run_rate_basic(self):
        now = datetime(2026, 10, 10, 2, 0, 0)
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-01", "product_name": "P1", "qty": 10, "channel": "shopee"}
        ]
        inventory = [
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 50, "channel": "shopee"}
        ]
        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        self.assertEqual(len(run_rates), 1)
        self.assertAlmostEqual(run_rates[0]["run_rate_per_hour"], 5.0, places=1)

    def test_stockout_prediction(self):
        now = datetime(2026, 10, 10, 2, 0, 0)
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-01", "product_name": "P1", "qty": 10, "channel": "shopee"}
        ]
        inventory = [
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 20, "channel": "shopee"}
        ]
        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        self.assertEqual(len(run_rates), 1)
        self.assertAlmostEqual(run_rates[0]["hours_until_stockout"], 4.0, places=1)
        self.assertIsNotNone(run_rates[0]["stockout_time"])

    def test_run_rate_zero_velocity(self):
        now = datetime(2026, 10, 10, 2, 0, 0)
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 02:00:00", "sku": "SKU-01", "product_name": "P1", "qty": 0, "channel": "shopee"}
        ]
        inventory = [
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 20, "channel": "shopee"}
        ]
        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        self.assertEqual(len(run_rates), 1)
        self.assertEqual(run_rates[0]["hours_until_stockout"], float("inf"))
        self.assertIsNone(run_rates[0]["stockout_time"])

    def test_run_rate_zero_stock(self):
        now = datetime(2026, 10, 10, 2, 0, 0)
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-01", "product_name": "P1", "qty": 10, "channel": "shopee"}
        ]
        inventory = [
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 0, "channel": "shopee"}
        ]
        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        self.assertEqual(len(run_rates), 1)
        self.assertEqual(run_rates[0]["hours_until_stockout"], 0.0)
        self.assertEqual(run_rates[0]["level"], "negative")

    def test_run_rate_sort_order(self):
        now = datetime(2026, 10, 10, 2, 0, 0)
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-INF", "product_name": "P0", "qty": 0, "channel": "shopee"},
            {"order_id": "O2", "created_at": "2026-10-10 00:00:00", "sku": "SKU-FAST", "product_name": "P1", "qty": 10, "channel": "shopee"}, # run rate 5/hr, stock 5 -> 1h
            {"order_id": "O3", "created_at": "2026-10-10 00:00:00", "sku": "SKU-SLOW", "product_name": "P2", "qty": 10, "channel": "shopee"}, # run rate 5/hr, stock 50 -> 10h
        ]
        inventory = [
            {"sku": "SKU-INF", "product_name": "P0", "channel_stock": 20, "channel": "shopee"},
            {"sku": "SKU-FAST", "product_name": "P1", "channel_stock": 5, "channel": "shopee"},
            {"sku": "SKU-SLOW", "product_name": "P2", "channel_stock": 50, "channel": "shopee"},
        ]
        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        self.assertEqual(run_rates[0]["sku"], "SKU-FAST")
        self.assertEqual(run_rates[1]["sku"], "SKU-SLOW")
        self.assertEqual(run_rates[2]["sku"], "SKU-INF")

    def test_rebalance_starved_channel(self):
        inventory = [
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 0, "channel": "shopee"},
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 30, "channel": "tiktok"},
        ]
        warehouse = {"SKU-01": 500}
        rebalance = calculate_rebalance(inventory, warehouse)
        self.assertEqual(len(rebalance), 1)
        self.assertEqual(rebalance[0]["sku"], "SKU-01")
        self.assertEqual(rebalance[0]["level"], "warning")
        self.assertTrue(any("Shopee" in rec for rec in rebalance[0]["recommendations"]))

    def test_rebalance_balanced_sku(self):
        inventory = [
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 50, "channel": "shopee"},
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 40, "channel": "tiktok"},
        ]
        warehouse = {"SKU-01": 200}
        rebalance = calculate_rebalance(inventory, warehouse)
        self.assertEqual(len(rebalance), 0)

    def test_rebalance_low_warehouse(self):
        inventory = [
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 0, "channel": "shopee"},
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 10, "channel": "tiktok"},
        ]
        warehouse = {"SKU-01": 30} # <= 50
        rebalance = calculate_rebalance(inventory, warehouse)
        self.assertEqual(len(rebalance), 0)

    def test_rebalance_warehouse_only_sku(self):
        inventory = []
        warehouse = {"SKU-WH-ONLY": 200}
        rebalance = calculate_rebalance(inventory, warehouse)
        self.assertEqual(len(rebalance), 1)
        self.assertEqual(rebalance[0]["shopee_stock"], 0)
        self.assertEqual(rebalance[0]["tiktok_stock"], 0)

    def test_budget_multi_quantity_loss(self):
        alerts = [
            {"order_id": "O1", "sku": "S1", "margin": -15000, "level": "negative", "qty": 4} # 60,000 loss
        ]
        budget = calculate_budget(alerts, campaign_budget=500000)
        self.assertEqual(budget["total_loss"], 60000)

    def test_budget_remaining_negative(self):
        alerts = [
            {"order_id": "O1", "sku": "S1", "margin": -50000, "level": "negative", "qty": 2} # 100,000 loss
        ]
        budget = calculate_budget(alerts, campaign_budget=80000)
        self.assertEqual(budget["total_loss"], 100000)
        self.assertEqual(budget["remaining"], -20000)
        self.assertAlmostEqual(budget["pct_used"], 125.0, places=1)
        self.assertEqual(budget["meter_level"], "over")

    def test_run_rate_multi_order_aggregation(self):
        now = datetime(2026, 10, 10, 2, 0, 0)
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-01", "product_name": "P1", "qty": 4, "channel": "shopee"},
            {"order_id": "O2", "created_at": "2026-10-10 01:00:00", "sku": "SKU-01", "product_name": "P1", "qty": 6, "channel": "shopee"},
        ]
        inventory = [
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 20, "channel": "shopee"}
        ]
        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        self.assertEqual(len(run_rates), 1)
        self.assertEqual(run_rates[0]["total_sold"], 10)
        self.assertAlmostEqual(run_rates[0]["run_rate_per_hour"], 5.0, places=1)

    def test_stockout_levels_classification(self):
        now = datetime(2026, 10, 10, 2, 0, 0)
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-CRIT", "product_name": "P1", "qty": 10, "channel": "shopee"}, # 5/hr, stock 5 -> 1h -> negative
            {"order_id": "O2", "created_at": "2026-10-10 00:00:00", "sku": "SKU-WARN", "product_name": "P2", "qty": 10, "channel": "shopee"}, # 5/hr, stock 20 -> 4h -> warning
            {"order_id": "O3", "created_at": "2026-10-10 00:00:00", "sku": "SKU-SAFE", "product_name": "P3", "qty": 10, "channel": "shopee"}, # 5/hr, stock 50 -> 10h -> positive
        ]
        inventory = [
            {"sku": "SKU-CRIT", "product_name": "P1", "channel_stock": 5, "channel": "shopee"},
            {"sku": "SKU-WARN", "product_name": "P2", "channel_stock": 20, "channel": "shopee"},
            {"sku": "SKU-SAFE", "product_name": "P3", "channel_stock": 50, "channel": "shopee"},
        ]
        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        rate_by_sku = {r["sku"]: r for r in run_rates}
        self.assertEqual(rate_by_sku["SKU-CRIT"]["level"], "negative")
        self.assertEqual(rate_by_sku["SKU-WARN"]["level"], "warning")
        self.assertEqual(rate_by_sku["SKU-SAFE"]["level"], "positive")

    def test_run_rate_inventory_without_orders_skipped(self):
        now = datetime(2026, 10, 10, 2, 0, 0)
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-SOLD", "product_name": "P1", "qty": 5, "channel": "shopee"}
        ]
        inventory = [
            {"sku": "SKU-SOLD", "product_name": "P1", "channel_stock": 20, "channel": "shopee"},
            {"sku": "SKU-NO-SALE", "product_name": "P2", "channel_stock": 50, "channel": "shopee"},
        ]
        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        skus = [r["sku"] for r in run_rates]
        self.assertIn("SKU-SOLD", skus)
        self.assertNotIn("SKU-NO-SALE", skus)

    def test_rebalance_recommendation_text_and_cap(self):
        inventory = [
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 2, "channel": "shopee"},
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 20, "channel": "tiktok"},
        ]
        warehouse = {"SKU-01": 500} # 500 // 2 = 250 -> capped at 100
        rebalance = calculate_rebalance(inventory, warehouse)
        self.assertEqual(len(rebalance), 1)
        self.assertIn("Replenish Shopee (+100 unit)", rebalance[0]["recommendations"])

    def test_rebalance_both_channels_starved(self):
        inventory = [
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 0, "channel": "shopee"},
            {"sku": "SKU-01", "product_name": "P1", "channel_stock": 3, "channel": "tiktok"},
        ]
        warehouse = {"SKU-01": 300}
        rebalance = calculate_rebalance(inventory, warehouse)
        self.assertEqual(len(rebalance), 1)
        recs = rebalance[0]["recommendations"]
        self.assertTrue(any("Shopee" in r for r in recs))
        self.assertTrue(any("TikTok" in r for r in recs))

    def test_rebalance_sort_order(self):
        inventory = [
            {"sku": "SKU-A", "product_name": "PA", "channel_stock": 0, "channel": "shopee"},
            {"sku": "SKU-B", "product_name": "PB", "channel_stock": 0, "channel": "shopee"},
        ]
        warehouse = {"SKU-A": 200, "SKU-B": 600}
        rebalance = calculate_rebalance(inventory, warehouse)
        self.assertEqual(rebalance[0]["sku"], "SKU-B")
        self.assertEqual(rebalance[1]["sku"], "SKU-A")


if __name__ == "__main__":
    unittest.main()

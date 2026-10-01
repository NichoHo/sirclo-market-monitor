"""
Phase 6: End-to-End Acceptance Verification & Polish Test Suite
SIRCLO Marketplace Monitor

Verifies:
1. 11 Acceptance Criteria (AC 1 - AC 11) from PRODUCT_SPEC.md.
2. Excel (.xlsx) ingestion in end-to-end analysis and COGS pipeline.
3. Performance benchmark: analysis execution speed < 2 seconds.
4. Edge cases: UTF-8 BOM, Latin-1, dot-separated thousands ("129.000"), empty CSVs, zero velocity, unmapped SKUs, budget bounds.
5. System guardrails non-interference with normal workflow.
6. Design and UX polish: strict zero-emoji policy, design tokens, tabular typography, single primary CTA, responsive viewports & safe areas.
7. WhatsApp summary & card copy exact format contracts.
"""

from datetime import datetime
import io
import math
import os
import re
import tempfile
import time
import unittest

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import openpyxl
except ImportError:
    openpyxl = None

from app import app
from db import init_db, bulk_insert_cogs, get_all_cogs
from engine import calculate_margins, calculate_budget, calculate_run_rate, calculate_rebalance
from summary import generate_summary_text, generate_alert_copy_text
from guardrails import reset_rate_limits, reset_in_flight_locks


class TestPhase6AcceptanceAndPolish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.data_dir = os.path.join(cls.root_dir, "data")
        cls.static_dir = os.path.join(cls.root_dir, "static")
        cls.templates_dir = os.path.join(cls.root_dir, "templates")

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        app.config["TESTING"] = True
        app.config["DB_PATH"] = self.db_path
        init_db(self.db_path)
        reset_rate_limits()
        reset_in_flight_locks()
        self.client = app.test_client()

    def tearDown(self):
        reset_rate_limits()
        reset_in_flight_locks()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def _get_sample_file(self, filename):
        path = os.path.join(self.data_dir, filename)
        with open(path, "rb") as f:
            return io.BytesIO(f.read()), filename

    def _seed_cogs_sample(self):
        cogs_io, cogs_name = self._get_sample_file("internal_cogs_hpp.csv")
        res = self.client.post("/api/cogs/upload", data={"cogs_file": (cogs_io, cogs_name)}, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        return res

    # =========================================================================
    # 1. End-to-End Acceptance Criteria 1 to 11 Integrated Verification
    # =========================================================================

    def test_p6_ac1_analysis_speed_benchmark(self):
        """AC 1: Upload 4 files + klik Analisis -> hasil muncul dalam < 30 detik. Target Polish: < 2.0 detik."""
        self._seed_cogs_sample()
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

        start = time.perf_counter()
        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        elapsed = time.perf_counter() - start

        self.assertEqual(res.status_code, 200)
        self.assertLess(elapsed, 2.0, f"Analysis took {elapsed:.3f}s, polished benchmark must be under 2.0s")

    def test_p6_ac2_all_negative_margins_detected(self):
        """AC 2: Semua order dengan harga jual aktual < HPP terdeteksi dan muncul di tab Jual Rugi."""
        self._seed_cogs_sample()
        res = self.client.get("/api/sample-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()

        alerts = body["margin_alerts"]
        negative_alerts = [a for a in alerts if a["level"] == "negative"]
        self.assertTrue(len(negative_alerts) >= 15, f"Expected >= 15 negative alerts, found {len(negative_alerts)}")
        for a in negative_alerts:
            self.assertLess(a["actual_unit_price"], a["hpp"])
            self.assertLess(a["margin"], 0)

    def test_p6_ac3_run_rate_accuracy(self):
        """AC 3: Run rate = total terjual / jam berjalan — akurat vs hitung manual."""
        now = datetime(2026, 10, 10, 4, 0, 0)
        orders = [
            {"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-A", "product_name": "Prod A", "qty": 20, "channel": "shopee"},
            {"order_id": "O2", "created_at": "2026-10-10 02:00:00", "sku": "SKU-A", "product_name": "Prod A", "qty": 10, "channel": "shopee"},
        ]
        inventory = [{"sku": "SKU-A", "product_name": "Prod A", "channel_stock": 60, "channel": "shopee"}]

        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        self.assertEqual(len(run_rates), 1)
        # 30 units over 4 hours = 7.5 units/hour
        self.assertAlmostEqual(run_rates[0]["run_rate_per_hour"], 7.5, places=2)

    def test_p6_ac4_stockout_prediction_tolerance(self):
        """AC 4: Prediksi habis = stok sisa / run rate — toleransi +- 15 menit."""
        now = datetime(2026, 10, 10, 2, 0, 0)
        orders = [{"order_id": "O1", "created_at": "2026-10-10 00:00:00", "sku": "SKU-B", "product_name": "Prod B", "qty": 10, "channel": "shopee"}]
        inventory = [{"sku": "SKU-B", "product_name": "Prod B", "channel_stock": 35, "channel": "shopee"}]

        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        # Rate: 5 units/hr. Stock: 35. Expected: 7.0 hours.
        self.assertAlmostEqual(run_rates[0]["hours_until_stockout"], 7.0, delta=0.25)

    def test_p6_ac5_budget_meter_sum(self):
        """AC 5: Budget meter = sum seluruh kerugian order yang jual di bawah HPP."""
        alerts = [
            {"order_id": "1", "sku": "S1", "margin": -20000, "level": "negative", "qty": 2}, # 40,000 loss
            {"order_id": "2", "sku": "S2", "margin": -10000, "level": "negative", "qty": 5}, # 50,000 loss
            {"order_id": "3", "sku": "S3", "margin": 5000, "level": "warning", "qty": 10},   # profit
        ]
        budget = calculate_budget(alerts, campaign_budget=200000)
        self.assertEqual(budget["total_loss"], 90000)
        self.assertEqual(budget["remaining"], 110000)
        self.assertEqual(budget["pct_used"], 45.0)
        self.assertEqual(budget["meter_level"], "safe")

    def test_p6_ac6_rebalancing_starved_skus(self):
        """AC 6: SKU dengan stok marketplace <= 5 dan warehouse > 50 muncul di tab Rebalancing."""
        inventory = [
            {"sku": "SKU-WH-1", "product_name": "Item 1", "channel_stock": 2, "channel": "shopee"},
            {"sku": "SKU-WH-1", "product_name": "Item 1", "channel_stock": 40, "channel": "tiktok"},
        ]
        warehouse = {"SKU-WH-1": 200}
        rebalance = calculate_rebalance(inventory, warehouse)

        self.assertEqual(len(rebalance), 1)
        self.assertEqual(rebalance[0]["sku"], "SKU-WH-1")
        self.assertIn("Replenish Shopee", rebalance[0]["recommendations"][0])

    def test_p6_ac7_alert_card_copy_format(self):
        """AC 7: Format copy card sesuai exact single-item action message template."""
        alert = {
            "order_id": "ORD999",
            "sku": "SKU-TEST-99",
            "product_name": "Hydra Facial Wash",
            "channel": "shopee",
            "actual_unit_price": 45000,
            "hpp": 60000,
            "margin": -15000,
        }
        text = generate_alert_copy_text(alert)
        expected = "ALERT: SKU-TEST-99 (Hydra Facial Wash) jual rugi -15000/unit di shopee. Harga jual Rp 45000, HPP Rp 60000. Segera cek voucher."
        self.assertEqual(text, expected)

    def test_p6_ac8_summary_text_complete(self):
        """AC 8: 'Salin Ringkasan' menghasilkan summary text lengkap seluruh 5 bagian."""
        budget_status = {"total_loss": 1000000, "campaign_budget": 5000000, "remaining": 4000000, "pct_used": 20.0, "meter_level": "safe"}
        alerts = [{"sku": "SKU-A", "channel": "shopee", "margin": -10000, "level": "negative"}]
        run_rates = [{"sku": "SKU-B", "channel": "tiktok", "stockout_time": "10 Okt 04:00", "hours_until_stockout": 2.5, "level": "warning"}]
        rebalance = [{"sku": "SKU-C", "warehouse_stock": 300, "shopee_stock": 1, "tiktok_stock": 20, "recommendations": ["Replenish Shopee (+100 unit)"]}]

        summary = generate_summary_text(alerts, budget_status, run_rates, rebalance, campaign_name="10.10 Midnight Sale")
        self.assertIn("RINGKASAN MARKETPLACE MONITOR", summary)
        self.assertIn("BUDGET:", summary)
        self.assertIn("ALERT JUAL RUGI", summary)
        self.assertIn("PREDIKSI HABIS", summary)
        self.assertIn("PERLU REPLENISH", summary)

    def test_p6_ac9_cogs_persistence(self):
        """AC 9: Data HPP persist setelah upload pertama — tidak hilang saat refresh."""
        self._seed_cogs_sample()
        # Verify persistence across separate client requests
        res1 = self.client.get("/api/cogs")
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.get_json()["count"], 50)

        res2 = self.client.get("/api/cogs")
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()["count"], 50)

    def test_p6_ac10_sample_data_demo(self):
        """AC 10: Tombol 'Muat Data Sample' berfungsi tanpa upload file."""
        res = self.client.get("/api/sample-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertIn("margin_alerts", body)
        self.assertIn("budget_status", body)
        self.assertIn("run_rate", body)
        self.assertIn("rebalance", body)
        self.assertIn("summary_text", body)

    def test_p6_ac11_zero_velocity_infinity(self):
        """AC 11: SKU tanpa penjualan (velocity = 0) -> prediksi habis = 'inf', bukan error."""
        now = datetime(2026, 10, 10, 1, 0, 0)
        orders = [{"order_id": "O1", "created_at": "2026-10-10 01:00:00", "sku": "SKU-INERT", "product_name": "Inert Item", "qty": 0, "channel": "shopee"}]
        inventory = [{"sku": "SKU-INERT", "product_name": "Inert Item", "channel_stock": 40, "channel": "shopee"}]

        run_rates = calculate_run_rate(orders, inventory, current_time=now)
        self.assertEqual(len(run_rates), 1)
        self.assertEqual(run_rates[0]["hours_until_stockout"], float("inf"))
        self.assertIsNone(run_rates[0]["stockout_time"])

    # =========================================================================
    # 2. Excel (.xlsx) Multi-Format Ingestion Tests
    # =========================================================================

    def _create_xlsx_bytes(self, headers, rows):
        """Generate binary content of an Excel .xlsx workbook in memory."""
        if openpyxl is None:
            self.skipTest("openpyxl not available")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for r in rows:
            ws.append(r)
        buf = io.BytesIO()
        wb.save(buf)
        wb.close()
        buf.seek(0)
        return buf

    def test_p6_excel_end_to_end_pipeline(self):
        """Test complete pipeline uploading real .xlsx files to /api/cogs/upload and /api/analyze."""
        if openpyxl is None:
            self.skipTest("openpyxl not available")

        # 1. COGS Excel
        cogs_headers = ["sku", "product_name", "category", "brand", "supplier", "hpp_per_unit"]
        cogs_rows = [
            ["SKU-XL-01", "Excel Moisture Cream", "Skincare", "BrandXL", "SupplierXL", 80000],
            ["SKU-XL-02", "Excel Sunscreen SPF50", "Skincare", "BrandXL", "SupplierXL", 70000],
        ]
        cogs_buf = self._create_xlsx_bytes(cogs_headers, cogs_rows)
        cogs_res = self.client.post("/api/cogs/upload", data={"cogs_file": (cogs_buf, "cogs.xlsx")}, content_type="multipart/form-data")
        self.assertEqual(cogs_res.status_code, 200)
        self.assertEqual(cogs_res.get_json()["inserted"], 2)

        # 2. Shopee Orders Excel
        sp_o_headers = ["order_id", "order_creation_time", "order_status", "sku_reference_no", "product_name", "quantity", "original_price", "real_selling_price_per_unit"]
        sp_o_rows = [
            ["XL-SP-001", "2026-10-10 00:30:00", "Completed", "SKU-XL-01", "Excel Moisture Cream", 1, 150000, 50000], # loss of 30,000
        ]
        sp_o_buf = self._create_xlsx_bytes(sp_o_headers, sp_o_rows)

        # 3. TikTok Orders Excel
        tt_o_headers = ["order_id", "created_time", "order_status", "seller_sku", "product_name", "quantity", "retail_price", "net_unit_settlement_price"]
        tt_o_rows = [
            ["XL-TT-001", "2026-10-10 01:00:00", "Completed", "SKU-XL-02", "Excel Sunscreen SPF50", 2, 120000, 60000], # loss of 10,000 x 2 = 20,000
        ]
        tt_o_buf = self._create_xlsx_bytes(tt_o_headers, tt_o_rows)

        # 4. Shopee Inventory Excel
        sp_i_headers = ["sku_reference_no", "product_name", "current_stock"]
        sp_i_rows = [["SKU-XL-01", "Excel Moisture Cream", 5]]
        sp_i_buf = self._create_xlsx_bytes(sp_i_headers, sp_i_rows)

        # 5. TikTok Inventory Excel
        tt_i_headers = ["seller_sku", "product_name", "available_stock"]
        tt_i_rows = [["SKU-XL-02", "Excel Sunscreen SPF50", 20]]
        tt_i_buf = self._create_xlsx_bytes(tt_i_headers, tt_i_rows)

        data = {
            "shopee_orders": (sp_o_buf, "sp_orders.xlsx"),
            "tiktok_orders": (tt_o_buf, "tt_orders.xlsx"),
            "shopee_inventory": (sp_i_buf, "sp_inv.xlsx"),
            "tiktok_inventory": (tt_i_buf, "tt_inv.xlsx"),
            "campaign_budget": "500000",
        }

        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()

        # Verify negative margin alerts
        self.assertEqual(len(body["margin_alerts"]), 2)
        # Total loss = 30,000 + 20,000 = 50,000
        self.assertEqual(body["budget_status"]["total_loss"], 50000)
        self.assertEqual(body["budget_status"]["remaining"], 450000)
        self.assertEqual(body["budget_status"]["pct_used"], 10.0)
        self.assertEqual(body["budget_status"]["meter_level"], "safe")

    # =========================================================================
    # 3. Robust Edge Case Ingestion Tests
    # =========================================================================

    def test_p6_edge_case_utf8_bom_and_latin1_orders(self):
        """CSV encoded with UTF-8 BOM and Latin-1 characters parsed accurately without UnicodeDecodeError."""
        self._seed_cogs_sample()
        bom_orders = (
            "\ufefforder_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
            "BOM01,2026-10-10 00:01:00,Completed,SKU-MOISTURIZER-01,Crème Hydratante,1,160000,50000\n"
        ).encode("utf-8-sig")

        tt_orders = (
            "order_id,created_time,order_status,seller_sku,product_name,quantity,retail_price,net_unit_settlement_price\n"
            "TT01,2026-10-10 00:02:00,Completed,SKU-SUNSCREEN-01,Soin Solaire SPF50,1,140000,40000\n"
        ).encode("latin-1")

        sp_inv = b"sku_reference_no,product_name,current_stock\nSKU-MOISTURIZER-01,Cream,10\n"
        tt_inv = b"seller_sku,product_name,available_stock\nSKU-SUNSCREEN-01,Sunscreen,10\n"

        data = {
            "shopee_orders": (io.BytesIO(bom_orders), "bom_orders.csv"),
            "tiktok_orders": (io.BytesIO(tt_orders), "latin_orders.csv"),
            "shopee_inventory": (io.BytesIO(sp_inv), "sp_inv.csv"),
            "tiktok_inventory": (io.BytesIO(tt_inv), "tt_inv.csv"),
            "campaign_budget": "5000000",
        }

        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(len(body["margin_alerts"]), 2)

    def test_p6_edge_case_indonesian_dot_separated_numbers(self):
        """Numeric values with Indonesian dot separators ('150.000', '45.000') parsed without ValueError."""
        self._seed_cogs_sample()
        sp_orders = (
            b"order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
            b"DOT01,2026-10-10 00:10:00,Completed,SKU-MOISTURIZER-01,Ceramide Cream,1,159.000,47.000\n"
        )
        tt_orders = (
            b"order_id,created_time,order_status,seller_sku,product_name,quantity,retail_price,net_unit_settlement_price\n"
            b"DOT02,2026-10-10 00:20:00,Completed,SKU-SUNSCREEN-01,Sunscreen SPF50,2,139.000,50.000\n"
        )
        sp_inv = b"sku_reference_no,product_name,current_stock\nSKU-MOISTURIZER-01,Cream,25.000\n"
        tt_inv = b"seller_sku,product_name,available_stock\nSKU-SUNSCREEN-01,Sunscreen,10.000\n"

        data = {
            "shopee_orders": (io.BytesIO(sp_orders), "dot_sp.csv"),
            "tiktok_orders": (io.BytesIO(tt_orders), "dot_tt.csv"),
            "shopee_inventory": (io.BytesIO(sp_inv), "dot_sp_inv.csv"),
            "tiktok_inventory": (io.BytesIO(tt_inv), "dot_tt_inv.csv"),
            "campaign_budget": "1.000.000",
        }

        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        # SKU-MOISTURIZER-01: HPP 80,000, sell 47,000 -> loss 33,000
        # SKU-SUNSCREEN-01: HPP 70,000, sell 50,000 -> loss 20,000 * 2 = 40,000
        # Total loss = 73,000
        self.assertEqual(body["budget_status"]["total_loss"], 73000)

    def test_p6_edge_case_empty_files_safe_handling(self):
        """Header-only files return 200 OK with empty arrays and safe meter without exceptions."""
        self._seed_cogs_sample()
        sp_o_header = b"order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
        tt_o_header = b"order_id,created_time,order_status,seller_sku,product_name,quantity,retail_price,net_unit_settlement_price\n"
        sp_i_header = b"sku_reference_no,product_name,current_stock\n"
        tt_i_header = b"seller_sku,product_name,available_stock\n"

        data = {
            "shopee_orders": (io.BytesIO(sp_o_header), "empty_sp_o.csv"),
            "tiktok_orders": (io.BytesIO(tt_o_header), "empty_tt_o.csv"),
            "shopee_inventory": (io.BytesIO(sp_i_header), "empty_sp_i.csv"),
            "tiktok_inventory": (io.BytesIO(tt_i_header), "empty_tt_i.csv"),
            "campaign_budget": "5000000",
        }

        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["margin_alerts"], [])
        self.assertEqual(body["run_rate"], [])
        self.assertEqual(body["budget_status"]["total_loss"], 0)
        self.assertEqual(body["budget_status"]["meter_level"], "safe")

    def test_p6_edge_case_unmapped_skus_warning(self):
        """Orders containing SKUs not present in COGS master are captured in unmapped_skus."""
        self._seed_cogs_sample()
        sp_orders = (
            b"order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
            b"ORD_UNKNOWN,2026-10-10 00:01:00,Completed,SKU-UNKNOWN-ITEM,Unknown Mystery Item,1,100000,50000\n"
        )
        tt_orders = (
            b"order_id,created_time,order_status,seller_sku,product_name,quantity,retail_price,net_unit_settlement_price\n"
            b"ORD_KNOWN,2026-10-10 00:02:00,Completed,SKU-SUNSCREEN-01,UV Shield Sunscreen,1,139000,50000\n"
        )
        sp_inv = b"sku_reference_no,product_name,current_stock\nSKU-UNKNOWN-ITEM,Mystery,10\n"
        tt_inv = b"seller_sku,product_name,available_stock\nSKU-SUNSCREEN-01,Sunscreen,10\n"

        data = {
            "shopee_orders": (io.BytesIO(sp_orders), "sp_orders.csv"),
            "tiktok_orders": (io.BytesIO(tt_orders), "tt_orders.csv"),
            "shopee_inventory": (io.BytesIO(sp_inv), "sp_inv.csv"),
            "tiktok_inventory": (io.BytesIO(tt_inv), "tt_inv.csv"),
            "campaign_budget": "5000000",
        }

        res = self.client.post("/api/analyze", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertIn("SKU-UNKNOWN-ITEM", body["unmapped_skus"])
        self.assertEqual(len(body["margin_alerts"]), 1)
        self.assertEqual(body["margin_alerts"][0]["sku"], "SKU-SUNSCREEN-01")

    def test_p6_edge_case_budget_zero_and_over_budget(self):
        """Budget 0 returns safe/0%; exceeded budget returns over/>100% with negative remaining."""
        # 1. Budget 0
        alerts = [{"sku": "S1", "margin": -10000, "qty": 1, "level": "negative"}]
        b_zero = calculate_budget(alerts, campaign_budget=0)
        self.assertEqual(b_zero["total_loss"], 10000)
        self.assertEqual(b_zero["pct_used"], 0.0)
        self.assertEqual(b_zero["meter_level"], "safe")

        # 2. Exceeded Budget
        b_over = calculate_budget(alerts, campaign_budget=5000)
        self.assertEqual(b_over["total_loss"], 10000)
        self.assertEqual(b_over["remaining"], -5000)
        self.assertEqual(b_over["pct_used"], 200.0)
        self.assertEqual(b_over["meter_level"], "over")

    # =========================================================================
    # 4. UX & Design Polish Compliance
    # =========================================================================

    def test_p6_ux_no_emoji_rule_across_project(self):
        """Zero emoji rule across templates/index.html, static/style.css, and static/app.js."""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"  # dingbats
            "\U0001F900-\U0001F9FF"  # supplemental symbols
            "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
            "]+",
            flags=re.UNICODE,
        )

        files_to_check = [
            os.path.join(self.templates_dir, "index.html"),
            os.path.join(self.static_dir, "style.css"),
            os.path.join(self.static_dir, "app.js"),
        ]

        for filepath in files_to_check:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            matches = emoji_pattern.findall(content)
            self.assertEqual(
                len(matches),
                0,
                f"File {os.path.basename(filepath)} contains forbidden emoji characters: {matches}",
            )

    def test_p6_ux_design_tokens_and_tabular_typography(self):
        """Verifies design tokens and OpenType tabular-nums typography in static/style.css."""
        css_path = os.path.join(self.static_dir, "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        tokens = [
            "--gray-50",
            "--gray-100",
            "--gray-200",
            "--gray-700",
            "--gray-900",
            "--blue-500",
            "--status-negative",
            "--meter-safe",
            "--meter-caution",
            "--meter-over",
            "--font-sans",
            "--font-mono",
        ]
        for t in tokens:
            self.assertIn(t, css, f"Missing design token {t} in style.css")

        self.assertIn("tabular-nums", css, "OpenType tabular-nums must be declared in style.css for aligned numeric display")

    def test_p6_ux_single_primary_cta_principle(self):
        """Ensures exactly 1 primary CTA button (btn-primary) exists in templates/index.html."""
        html_path = os.path.join(self.templates_dir, "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        primary_matches = re.findall(r'class="[^"]*\bbtn-primary\b[^"]*"', html)
        self.assertEqual(len(primary_matches), 1, f"Expected exactly 1 btn-primary, found {len(primary_matches)}")

    def test_p6_ux_responsive_layout_and_safe_areas(self):
        """Verifies mobile responsiveness and iOS safe-area-inset declarations in style.css."""
        css_path = os.path.join(self.static_dir, "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        self.assertIn("@media", css, "Media queries must be present in style.css")
        self.assertIn("safe-area-inset-top", css, "iOS safe-area-inset-top must be present for mobile notch ergonomics")
        self.assertIn("safe-area-inset-bottom", css, "iOS safe-area-inset-bottom must be present for mobile gesture bar ergonomics")


if __name__ == "__main__":
    unittest.main()

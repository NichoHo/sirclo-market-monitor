import os
import unittest

# Allow importing from project root
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from parser import (
        parse_shopee_orders,
        parse_tiktok_orders,
        parse_shopee_inventory,
        parse_tiktok_inventory,
        parse_cogs_csv,
        parse_warehouse_inventory,
    )
except ImportError:
    pass


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

    def test_parse_shopee_orders(self):
        file_path = os.path.join(self.data_dir, "shopee_orders.csv")
        with open(file_path, "rb") as f:
            content = f.read()
        rows, warnings = parse_shopee_orders(content)
        self.assertEqual(len(rows), 50)
        self.assertEqual(rows[0]["channel"], "shopee")
        required_keys = {"order_id", "created_at", "sku", "product_name", "qty", "original_price", "actual_unit_price", "channel"}
        self.assertTrue(required_keys.issubset(rows[0].keys()))

    def test_parse_tiktok_orders(self):
        file_path = os.path.join(self.data_dir, "tiktok_orders.csv")
        with open(file_path, "rb") as f:
            content = f.read()
        rows, warnings = parse_tiktok_orders(content)
        self.assertEqual(len(rows), 50)
        self.assertEqual(rows[0]["channel"], "tiktok")
        required_keys = {"order_id", "created_at", "sku", "product_name", "qty", "original_price", "actual_unit_price", "channel"}
        self.assertTrue(required_keys.issubset(rows[0].keys()))

    def test_parse_shopee_inventory(self):
        file_path = os.path.join(self.data_dir, "shopee_inventory.csv")
        with open(file_path, "rb") as f:
            content = f.read()
        rows, warnings = parse_shopee_inventory(content)
        self.assertEqual(len(rows), 50)
        self.assertEqual(rows[0]["channel"], "shopee")
        required_keys = {"sku", "product_name", "channel_stock", "channel"}
        self.assertTrue(required_keys.issubset(rows[0].keys()))

    def test_parse_tiktok_inventory(self):
        file_path = os.path.join(self.data_dir, "tiktok_inventory.csv")
        with open(file_path, "rb") as f:
            content = f.read()
        rows, warnings = parse_tiktok_inventory(content)
        self.assertEqual(len(rows), 50)
        self.assertEqual(rows[0]["channel"], "tiktok")
        required_keys = {"sku", "product_name", "channel_stock", "channel"}
        self.assertTrue(required_keys.issubset(rows[0].keys()))

    def test_parse_cogs_csv(self):
        file_path = os.path.join(self.data_dir, "internal_cogs_hpp.csv")
        with open(file_path, "rb") as f:
            content = f.read()
        rows, warnings = parse_cogs_csv(content)
        self.assertEqual(len(rows), 50)
        required_keys = {"sku", "product_name", "category", "brand", "supplier", "hpp_per_unit"}
        self.assertTrue(required_keys.issubset(rows[0].keys()))

    def test_parse_missing_required_column(self):
        bad_csv = b"order_id,order_status\n101,Completed\n"
        with self.assertRaises(Exception) as ctx:
            parse_shopee_orders(bad_csv)
        self.assertIn("sku", str(ctx.exception).lower())

    def test_parse_invalid_row_warning(self):
        csv_data = (
            b"order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
            b"ORD01,2026-10-10 00:01:00,Completed,SKU-01,Product 1,invalid_qty,100000,90000\n"
            b"ORD02,2026-10-10 00:02:00,Completed,SKU-02,Product 2,2,100000,90000\n"
        )
        rows, warnings = parse_shopee_orders(csv_data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["order_id"], "ORD02")
        self.assertTrue(len(warnings) > 0)
        self.assertTrue(any("invalid_qty" in w or "quantity" in w.lower() for w in warnings))

    def test_parse_empty_csv(self):
        header_only = b"order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
        rows, warnings = parse_shopee_orders(header_only)
        self.assertEqual(rows, [])
        self.assertEqual(warnings, [])

    def test_parse_dot_separated_numbers(self):
        csv_data = (
            b"order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
            b"ORD01,2026-10-10 00:01:00,Completed,SKU-01,Product 1,1,129.000,99.000\n"
        )
        rows, warnings = parse_shopee_orders(csv_data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["original_price"], 129000)
        self.assertEqual(rows[0]["actual_unit_price"], 99000)

    def test_parse_utf8_bom(self):
        csv_data = (
            b"\xef\xbb\xbforder_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
            b"ORD01,2026-10-10 00:01:00,Completed,SKU-01,Product 1,1,100000,90000\n"
        )
        rows, warnings = parse_shopee_orders(csv_data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["order_id"], "ORD01")

    def test_parse_latin1_encoding(self):
        csv_text = (
            "order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
            "ORD01,2026-10-10 00:01:00,Completed,SKU-01,Crème Café,1,100000,90000\n"
        )
        latin1_bytes = csv_text.encode("latin-1")
        rows, warnings = parse_shopee_orders(latin1_bytes)
        self.assertEqual(len(rows), 1)
        self.assertIn("Cr", rows[0]["product_name"])

    def test_parse_case_insensitive_whitespace_headers(self):
        csv_data = (
            b" ORDER_ID , Order_Creation_Time , ORDER_STATUS , SKU_Reference_No , Product_Name , Quantity , Original_Price , Real_Selling_Price_Per_Unit \n"
            b"ORD01,2026-10-10 00:01:00,Completed,SKU-01,Product 1,1,100000,90000\n"
        )
        rows, warnings = parse_shopee_orders(csv_data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sku"], "SKU-01")

    def test_parse_warehouse_inventory(self):
        file_path = os.path.join(self.data_dir, "master_warehouse_inventory_cogs.csv")
        with open(file_path, "rb") as f:
            content = f.read()
        wh_stock, warnings = parse_warehouse_inventory(content)
        self.assertIsInstance(wh_stock, dict)
        self.assertTrue(len(wh_stock) >= 50)
        self.assertIn("SKU-LIP-VELVET-01", wh_stock)
        self.assertIsInstance(wh_stock["SKU-LIP-VELVET-01"], int)

    def test_parse_duplicate_order_ids_preserved(self):
        csv_data = (
            b"order_id,order_creation_time,order_status,sku_reference_no,product_name,quantity,original_price,real_selling_price_per_unit\n"
            b"ORD01,2026-10-10 00:01:00,Completed,SKU-01,Product 1,1,100000,90000\n"
            b"ORD01,2026-10-10 00:01:00,Completed,SKU-02,Product 2,2,80000,70000\n"
        )
        rows, warnings = parse_shopee_orders(csv_data)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["order_id"], "ORD01")
        self.assertEqual(rows[1]["order_id"], "ORD01")
        self.assertEqual(rows[0]["sku"], "SKU-01")
        self.assertEqual(rows[1]["sku"], "SKU-02")

    def test_parse_corrupted_file_error(self):
        corrupted_data = b"\x00\xff\xfe\x00\x12\x34\x56\x78\x90"
        with self.assertRaises(Exception):
            parse_shopee_orders(corrupted_data)


if __name__ == "__main__":
    unittest.main()

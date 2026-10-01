import os
import sqlite3
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from db import (
        init_db,
        bulk_insert_cogs,
        get_all_cogs,
        get_all_cogs_rows,
        get_cogs_by_sku,
        update_cogs,
        delete_cogs,
    )
except ImportError:
    pass


class TestDB(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_db_init(self):
        init_db(self.db_path)
        self.assertTrue(os.path.exists(self.db_path))

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(cogs)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        expected = {"sku", "product_name", "category", "brand", "supplier", "hpp_per_unit", "last_updated"}
        self.assertTrue(expected.issubset(columns))

    def test_db_bulk_insert(self):
        init_db(self.db_path)
        sample_rows = [
            {
                "sku": f"SKU-{i:03d}",
                "product_name": f"Product {i}",
                "category": "Beauty",
                "brand": "BrandA",
                "supplier": "SupplierX",
                "hpp_per_unit": 50000 + i * 1000,
                "last_updated": "2026-10-01",
            }
            for i in range(50)
        ]
        inserted = bulk_insert_cogs(sample_rows, self.db_path)
        self.assertEqual(inserted, 50)

        rows = get_all_cogs_rows(self.db_path)
        self.assertEqual(len(rows), 50)

    def test_db_upsert(self):
        init_db(self.db_path)
        initial_row = [
            {"sku": "SKU-001", "product_name": "Old Name", "category": "Cat", "brand": "Brand", "supplier": "Sup", "hpp_per_unit": 50000, "last_updated": "2026-10-01"}
        ]
        bulk_insert_cogs(initial_row, self.db_path)

        updated_row = [
            {"sku": "SKU-001", "product_name": "New Name", "category": "Cat", "brand": "Brand", "supplier": "Sup", "hpp_per_unit": 65000, "last_updated": "2026-10-02"}
        ]
        bulk_insert_cogs(updated_row, self.db_path)

        rows = get_all_cogs_rows(self.db_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_name"], "New Name")
        self.assertEqual(rows[0]["hpp_per_unit"], 65000)

    def test_db_update_single(self):
        init_db(self.db_path)
        sample_rows = [
            {"sku": "SKU-001", "product_name": "P1", "category": "C", "brand": "B", "supplier": "S", "hpp_per_unit": 50000, "last_updated": "2026-10-01"},
            {"sku": "SKU-002", "product_name": "P2", "category": "C", "brand": "B", "supplier": "S", "hpp_per_unit": 70000, "last_updated": "2026-10-01"},
        ]
        bulk_insert_cogs(sample_rows, self.db_path)

        success = update_cogs("SKU-001", 55000, self.db_path)
        self.assertTrue(success)

        cogs_dict = get_all_cogs(self.db_path)
        self.assertEqual(cogs_dict["SKU-001"], 55000)
        self.assertEqual(cogs_dict["SKU-002"], 70000)

    def test_db_delete_single(self):
        init_db(self.db_path)
        sample_rows = [
            {"sku": "SKU-001", "product_name": "P1", "category": "C", "brand": "B", "supplier": "S", "hpp_per_unit": 50000, "last_updated": "2026-10-01"},
            {"sku": "SKU-002", "product_name": "P2", "category": "C", "brand": "B", "supplier": "S", "hpp_per_unit": 70000, "last_updated": "2026-10-01"},
        ]
        bulk_insert_cogs(sample_rows, self.db_path)

        success = delete_cogs("SKU-001", self.db_path)
        self.assertTrue(success)

        cogs_dict = get_all_cogs(self.db_path)
        self.assertEqual(len(cogs_dict), 1)
        self.assertNotIn("SKU-001", cogs_dict)
        self.assertIn("SKU-002", cogs_dict)

    def test_db_get_all_cogs_dict(self):
        init_db(self.db_path)
        sample_rows = [
            {"sku": "SKU-001", "product_name": "P1", "category": "C", "brand": "B", "supplier": "S", "hpp_per_unit": 50000, "last_updated": "2026-10-01"},
            {"sku": "SKU-002", "product_name": "P2", "category": "C", "brand": "B", "supplier": "S", "hpp_per_unit": 70000, "last_updated": "2026-10-01"},
        ]
        bulk_insert_cogs(sample_rows, self.db_path)

        cogs_dict = get_all_cogs(self.db_path)
        self.assertEqual(cogs_dict, {"SKU-001": 50000, "SKU-002": 70000})

    def test_db_get_cogs_by_sku(self):
        init_db(self.db_path)
        sample_rows = [
            {"sku": "SKU-SUNSCREEN-01", "product_name": "Sunscreen", "category": "Skincare", "brand": "Glow", "supplier": "Factory1", "hpp_per_unit": 70000, "last_updated": "2026-10-01"}
        ]
        bulk_insert_cogs(sample_rows, self.db_path)

        item = get_cogs_by_sku("SKU-SUNSCREEN-01", self.db_path)
        self.assertIsNotNone(item)
        self.assertEqual(item["sku"], "SKU-SUNSCREEN-01")
        self.assertEqual(item["hpp_per_unit"], 70000)

        missing = get_cogs_by_sku("SKU-NONEXISTENT", self.db_path)
        self.assertIsNone(missing)

    def test_db_empty_database(self):
        init_db(self.db_path)
        cogs_dict = get_all_cogs(self.db_path)
        self.assertEqual(cogs_dict, {})

        rows = get_all_cogs_rows(self.db_path)
        self.assertEqual(rows, [])

    def test_db_update_preserves_other_columns(self):
        init_db(self.db_path)
        sample_row = [
            {"sku": "SKU-001", "product_name": "Original Name", "category": "Skincare", "brand": "BrandX", "supplier": "SupplierY", "hpp_per_unit": 50000, "last_updated": "2026-10-01"}
        ]
        bulk_insert_cogs(sample_row, self.db_path)

        update_cogs("SKU-001", 62000, self.db_path)

        updated_item = get_cogs_by_sku("SKU-001", self.db_path)
        self.assertEqual(updated_item["hpp_per_unit"], 62000)
        self.assertEqual(updated_item["product_name"], "Original Name")
        self.assertEqual(updated_item["category"], "Skincare")
        self.assertEqual(updated_item["brand"], "BrandX")
        self.assertEqual(updated_item["supplier"], "SupplierY")


if __name__ == "__main__":
    unittest.main()

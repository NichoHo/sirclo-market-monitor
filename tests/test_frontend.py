import os
import re
import unittest

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestFrontend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.template_path = os.path.join(cls.root_dir, "templates", "index.html")
        cls.css_path = os.path.join(cls.root_dir, "static", "style.css")

    def _read_template(self):
        if not os.path.exists(self.template_path):
            self.skipTest(f"{self.template_path} does not exist yet")
        with open(self.template_path, "r", encoding="utf-8") as f:
            return f.read()

    def _read_css(self):
        if not os.path.exists(self.css_path):
            self.skipTest(f"{self.css_path} does not exist yet")
        with open(self.css_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_frontend_upload_slots_present(self):
        html = self._read_template()
        inputs = ["shopee_orders", "tiktok_orders", "shopee_inventory", "tiktok_inventory"]
        for inp in inputs:
            self.assertTrue(inp in html, f"Upload slot input '{inp}' missing from HTML")

    def test_frontend_tabs_present(self):
        html = self._read_template()
        tabs = ["Jual Rugi", "Prediksi Habis", "Rebalancing"]
        for tab in tabs:
            self.assertTrue(tab in html, f"Tab '{tab}' missing from HTML")

    def test_frontend_budget_meter_elements(self):
        html = self._read_template()
        self.assertTrue("budget" in html.lower())
        self.assertTrue("progress" in html.lower() or "meter" in html.lower())

    def test_frontend_design_tokens_css(self):
        css = self._read_css()
        tokens = [
            "--gray-50",
            "--gray-100",
            "--gray-200",
            "--gray-500",
            "--gray-900",
            "--status-negative",
            "--status-warning",
            "--status-positive",
            "--meter-safe",
            "--meter-caution",
            "--meter-over",
            "--font-sans",
            "--font-mono",
        ]
        for token in tokens:
            self.assertIn(token, css, f"Design token '{token}' missing from style.css")

    def test_frontend_no_emoji_rule(self):
        html = self._read_template()
        css = self._read_css()

        # Unicode regex matching emojis (symbols, pictographs, transport/map, dingbats)
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F]|"  # emoticons
            r"[\U0001F300-\U0001F5FF]|"  # symbols & pictographs
            r"[\U0001F680-\U0001F6FF]|"  # transport & map
            r"[\U0001F1E0-\U0001F1FF]|"  # flags
            r"[\U00002702-\U000027B0]|"  # dingbats
            r"[\U000024C2-\U0001F251]|"
            r"[\U0001F900-\U0001F9FF]|"  # supplemental symbols
            r"[\U0001FA70-\U0001FAFF]"   # symbols extended-a
        )
        self.assertFalse(emoji_pattern.search(html), "Found emoji in templates/index.html (violates design.md rule)")
        self.assertFalse(emoji_pattern.search(css), "Found emoji in static/style.css (violates design.md rule)")

    def test_frontend_toast_element_present(self):
        html = self._read_template()
        self.assertTrue("toast" in html.lower(), "Toast container missing from HTML")

    def test_frontend_copy_summary_button_present(self):
        html = self._read_template()
        self.assertTrue("Salin Ringkasan" in html, "'Salin Ringkasan' button missing from HTML")

    def test_frontend_cogs_section_present(self):
        html = self._read_template()
        self.assertTrue("cogs" in html.lower() or "hpp" in html.lower(), "COGS / HPP management section missing from HTML")

    def test_frontend_file_accept_attributes(self):
        html = self._read_template()
        self.assertIn(".xlsx", html, "Excel .xlsx missing from file accept attributes")
        self.assertIn(".csv", html, "CSV missing from file accept attributes")
        self.assertIn(".tsv", html, "TSV missing from file accept attributes")

    def test_frontend_error_banner_present(self):
        html = self._read_template()
        self.assertIn("error-banner", html, "Error banner missing from HTML")

    def test_frontend_run_rate_table_columns(self):
        html = self._read_template()
        expected_columns = ["SKU", "Channel", "Terjual", "Run Rate/Jam", "Stok", "Prediksi Habis", "Status"]
        for col in expected_columns:
            self.assertIn(col, html, f"Table column '{col}' missing from HTML")

    def test_frontend_cogs_drawer_present(self):
        html = self._read_template()
        self.assertIn("cogs-drawer", html, "COGS drawer missing from HTML")
        self.assertIn("cogs-table-body", html, "COGS table body missing from HTML")

    def test_frontend_single_primary_cta_rule(self):
        html = self._read_template()
        # Find all btn-primary occurrences
        matches = re.findall(r'class="[^"]*btn-primary[^"]*"', html)
        self.assertEqual(len(matches), 1, "Violates 1 Action Per Page: Expected exactly 1 btn-primary CTA")

    def test_frontend_no_emoji_in_js(self):
        js_path = os.path.join(self.root_dir, "static", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F]|"
            r"[\U0001F300-\U0001F5FF]|"
            r"[\U0001F680-\U0001F6FF]|"
            r"[\U0001F1E0-\U0001F1FF]|"
            r"[\U00002702-\U000027B0]|"
            r"[\U000024C2-\U0001F251]|"
            r"[\U0001F900-\U0001F9FF]|"
            r"[\U0001FA70-\U0001FAFF]"
        )
        self.assertFalse(emoji_pattern.search(js_content), "Found emoji in static/app.js (violates design.md rule)")


if __name__ == "__main__":
    unittest.main()

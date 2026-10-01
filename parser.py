import csv
import io
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

try:
    import openpyxl
except ImportError:
    openpyxl = None

MAX_ROW_LIMIT = 50000


def clean_int(val: Any) -> int:
    """Parse numeric values with Indonesian dot thousand separators, commas, or floats."""
    if val is None:
        raise ValueError("Nilai kosong")
    if isinstance(val, (int,)):
        return val
    if isinstance(val, float):
        return int(round(val))

    s = str(val).strip()
    if not s:
        raise ValueError("Nilai kosong")

    # If format like "129.000" or "129,000", strip dots and commas
    cleaned = s.replace(".", "").replace(",", "").strip()
    return int(cleaned)


def read_tabular_rows(file_content: bytes, filename: str = "") -> List[Dict[str, Any]]:
    """
    Read tabular file (CSV, TSV, or Excel .xlsx/.xls) into a list of row dicts.
    Header keys are preserved in original format but stripped of leading/trailing whitespace.
    """
    if not file_content:
        return []

    # Check for Excel file
    is_excel = filename.lower().endswith((".xlsx", ".xlsm")) or file_content.startswith(b"PK\x03\x04")

    if is_excel:
        if openpyxl is None:
            raise RuntimeError("Pustaka 'openpyxl' diperlukan untuk membaca file Excel")
        wb = None
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True, read_only=False)
            sheet = wb.active
            rows_iter = sheet.iter_rows(values_only=True)
            try:
                header_row = next(rows_iter)
            except StopIteration:
                return []

            if not header_row:
                return []

            headers = [str(c).strip() if c is not None else "" for c in header_row]
            # Filter out empty trailing headers
            while headers and not headers[-1]:
                headers.pop()

            if not headers:
                return []

            data_rows = []
            for r in rows_iter:
                if r is None or not any(c is not None for c in r):
                    continue
                row_dict = {}
                for idx, h in enumerate(headers):
                    if h:
                        val = r[idx] if idx < len(r) else None
                        row_dict[h] = val
                data_rows.append(row_dict)
                if len(data_rows) > MAX_ROW_LIMIT:
                    raise ValueError(f"File melebihi batas maksimal {MAX_ROW_LIMIT} baris")
            return data_rows
        except Exception as e:
            if "batas maksimal" in str(e):
                raise
            raise ValueError(f"Gagal membaca file Excel: {e}")
        finally:
            if wb is not None:
                wb.close()

    # Check for binary corruption in non-Excel files
    if b"\x00" in file_content:
        raise ValueError("File biner atau format tidak didukung / rusak")

    # Try decoding text
    decoded_text = None
    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
        try:
            decoded_text = file_content.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if decoded_text is None:
        raise ValueError("Gagal membaca enkripsi file CSV")

    lines = [line for line in decoded_text.splitlines() if line.strip()]
    if not lines:
        return []

    # Detect delimiter
    first_line = lines[0]
    if filename.lower().endswith(".tsv") or ("\t" in first_line and "," not in first_line):
        delimiter = "\t"
    elif ";" in first_line and "," not in first_line:
        delimiter = ";"
    else:
        delimiter = ","

    reader = csv.reader(io.StringIO(decoded_text), delimiter=delimiter)
    try:
        header_row = next(reader)
    except StopIteration:
        return []

    headers = [h.strip().lstrip('\ufeff') for h in header_row]
    # Filter empty trailing headers
    while headers and not headers[-1]:
        headers.pop()

    if not headers:
        return []

    data_rows = []
    for r in reader:
        if not r or not any(c.strip() for c in r):
            continue
        row_dict = {}
        for idx, h in enumerate(headers):
            if h:
                row_dict[h] = r[idx].strip() if idx < len(r) else ""
        data_rows.append(row_dict)
        if len(data_rows) > MAX_ROW_LIMIT:
            raise ValueError(f"File melebihi batas maksimal {MAX_ROW_LIMIT} baris")

    return data_rows


def _find_column(headers_map: Dict[str, str], candidates: List[str]) -> Optional[str]:
    """Find the original header string that matches any candidate (case-insensitive)."""
    for cand in candidates:
        cand_lower = cand.lower().strip()
        if cand_lower in headers_map:
            return headers_map[cand_lower]
    return None


def parse_shopee_orders(file_content: bytes, filename: str = "") -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parse Shopee orders tabular file into internal OrderRow schema."""
    raw_rows = read_tabular_rows(file_content, filename)
    if not raw_rows:
        return [], []

    # Build case-insensitive header lookup
    headers_map = {k.strip().lower(): k for k in raw_rows[0].keys()}

    # Required column definitions (primary name, aliases)
    req_specs = [
        ("sku_reference_no", ["sku_reference_no", "sku", "seller_sku"]),
        ("order_id", ["order_id"]),
        ("order_creation_time", ["order_creation_time", "created_at", "order_time"]),
        ("order_status", ["order_status", "status"]),
        ("product_name", ["product_name", "item_name"]),
        ("quantity", ["quantity", "qty"]),
        ("original_price", ["original_price", "retail_price"]),
        ("real_selling_price_per_unit", ["real_selling_price_per_unit", "actual_unit_price", "actual_price"]),
    ]

    col_map = {}
    for primary_col, aliases in req_specs:
        found = _find_column(headers_map, aliases)
        if not found:
            raise ValueError(f"Kolom '{primary_col}' tidak ditemukan di file Shopee Orders")
        col_map[primary_col] = found

    parsed_rows: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for idx, r in enumerate(raw_rows, start=2):
        try:
            qty = clean_int(r.get(col_map["quantity"]))
        except Exception:
            warnings.append(f"Row {idx}: kolom 'quantity' bukan angka ('{r.get(col_map['quantity'])}'), row dilewati")
            continue

        try:
            orig_price = clean_int(r.get(col_map["original_price"]))
        except Exception:
            warnings.append(f"Row {idx}: kolom 'original_price' bukan angka ('{r.get(col_map['original_price'])}'), row dilewati")
            continue

        try:
            actual_price = clean_int(r.get(col_map["real_selling_price_per_unit"]))
        except Exception:
            warnings.append(f"Row {idx}: kolom 'real_selling_price_per_unit' bukan angka ('{r.get(col_map['real_selling_price_per_unit'])}'), row dilewati")
            continue

        order_row = {
            "order_id": str(r.get(col_map["order_id"], "")).strip(),
            "created_at": str(r.get(col_map["order_creation_time"], "")).strip(),
            "status": str(r.get(col_map["order_status"], "")).strip(),
            "sku": str(r.get(col_map["sku_reference_no"], "")).strip(),
            "product_name": str(r.get(col_map["product_name"], "")).strip(),
            "qty": qty,
            "original_price": orig_price,
            "actual_unit_price": actual_price,
            "channel": "shopee",
        }
        parsed_rows.append(order_row)

    return parsed_rows, warnings


def parse_tiktok_orders(file_content: bytes, filename: str = "") -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parse TikTok orders tabular file into internal OrderRow schema."""
    raw_rows = read_tabular_rows(file_content, filename)
    if not raw_rows:
        return [], []

    headers_map = {k.strip().lower(): k for k in raw_rows[0].keys()}

    req_specs = [
        ("seller_sku", ["seller_sku", "sku_reference_no", "sku"]),
        ("order_id", ["order_id"]),
        ("created_time", ["created_time", "order_creation_time", "created_at"]),
        ("order_status", ["order_status", "status"]),
        ("product_name", ["product_name", "item_name"]),
        ("quantity", ["quantity", "qty"]),
        ("retail_price", ["retail_price", "original_price"]),
        ("net_unit_settlement_price", ["net_unit_settlement_price", "actual_unit_price", "real_selling_price_per_unit"]),
    ]

    col_map = {}
    for primary_col, aliases in req_specs:
        found = _find_column(headers_map, aliases)
        if not found:
            raise ValueError(f"Kolom '{primary_col}' tidak ditemukan di file TikTok Orders")
        col_map[primary_col] = found

    parsed_rows: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for idx, r in enumerate(raw_rows, start=2):
        try:
            qty = clean_int(r.get(col_map["quantity"]))
        except Exception:
            warnings.append(f"Row {idx}: kolom 'quantity' bukan angka ('{r.get(col_map['quantity'])}'), row dilewati")
            continue

        try:
            orig_price = clean_int(r.get(col_map["retail_price"]))
        except Exception:
            warnings.append(f"Row {idx}: kolom 'retail_price' bukan angka ('{r.get(col_map['retail_price'])}'), row dilewati")
            continue

        try:
            actual_price = clean_int(r.get(col_map["net_unit_settlement_price"]))
        except Exception:
            warnings.append(f"Row {idx}: kolom 'net_unit_settlement_price' bukan angka ('{r.get(col_map['net_unit_settlement_price'])}'), row dilewati")
            continue

        order_row = {
            "order_id": str(r.get(col_map["order_id"], "")).strip(),
            "created_at": str(r.get(col_map["created_time"], "")).strip(),
            "status": str(r.get(col_map["order_status"], "")).strip(),
            "sku": str(r.get(col_map["seller_sku"], "")).strip(),
            "product_name": str(r.get(col_map["product_name"], "")).strip(),
            "qty": qty,
            "original_price": orig_price,
            "actual_unit_price": actual_price,
            "channel": "tiktok",
        }
        parsed_rows.append(order_row)

    return parsed_rows, warnings


def parse_shopee_inventory(file_content: bytes, filename: str = "") -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parse Shopee inventory tabular file into internal InventoryRow schema."""
    raw_rows = read_tabular_rows(file_content, filename)
    if not raw_rows:
        return [], []

    headers_map = {k.strip().lower(): k for k in raw_rows[0].keys()}

    req_specs = [
        ("sku_reference_no", ["sku_reference_no", "sku", "seller_sku"]),
        ("product_name", ["product_name", "item_name"]),
        ("current_stock", ["current_stock", "available_stock", "stock", "quantity"]),
    ]

    col_map = {}
    for primary_col, aliases in req_specs:
        found = _find_column(headers_map, aliases)
        if not found:
            raise ValueError(f"Kolom '{primary_col}' tidak ditemukan di file Shopee Inventory")
        col_map[primary_col] = found

    parsed_rows: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for idx, r in enumerate(raw_rows, start=2):
        try:
            stock = clean_int(r.get(col_map["current_stock"]))
        except Exception:
            warnings.append(f"Row {idx}: kolom 'current_stock' bukan angka ('{r.get(col_map['current_stock'])}'), row dilewati")
            continue

        inv_row = {
            "sku": str(r.get(col_map["sku_reference_no"], "")).strip(),
            "product_name": str(r.get(col_map["product_name"], "")).strip(),
            "channel_stock": stock,
            "channel": "shopee",
        }
        parsed_rows.append(inv_row)

    return parsed_rows, warnings


def parse_tiktok_inventory(file_content: bytes, filename: str = "") -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parse TikTok inventory tabular file into internal InventoryRow schema."""
    raw_rows = read_tabular_rows(file_content, filename)
    if not raw_rows:
        return [], []

    headers_map = {k.strip().lower(): k for k in raw_rows[0].keys()}

    req_specs = [
        ("seller_sku", ["seller_sku", "sku_reference_no", "sku"]),
        ("product_name", ["product_name", "item_name"]),
        ("available_stock", ["available_stock", "current_stock", "stock", "quantity"]),
    ]

    col_map = {}
    for primary_col, aliases in req_specs:
        found = _find_column(headers_map, aliases)
        if not found:
            raise ValueError(f"Kolom '{primary_col}' tidak ditemukan di file TikTok Inventory")
        col_map[primary_col] = found

    parsed_rows: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for idx, r in enumerate(raw_rows, start=2):
        try:
            stock = clean_int(r.get(col_map["available_stock"]))
        except Exception:
            warnings.append(f"Row {idx}: kolom 'available_stock' bukan angka ('{r.get(col_map['available_stock'])}'), row dilewati")
            continue

        inv_row = {
            "sku": str(r.get(col_map["seller_sku"], "")).strip(),
            "product_name": str(r.get(col_map["product_name"], "")).strip(),
            "channel_stock": stock,
            "channel": "tiktok",
        }
        parsed_rows.append(inv_row)

    return parsed_rows, warnings


def parse_cogs_csv(file_content: bytes, filename: str = "") -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parse COGS tabular file into list of COGSRow dicts."""
    raw_rows = read_tabular_rows(file_content, filename)
    if not raw_rows:
        return [], []

    headers_map = {k.strip().lower(): k for k in raw_rows[0].keys()}

    req_specs = [
        ("sku", ["sku", "sku_reference_no", "seller_sku"]),
        ("product_name", ["product_name", "item_name"]),
        ("hpp_per_unit", ["hpp_per_unit", "hpp_per_unit_idr", "cogs_idr", "hpp"]),
    ]

    col_map = {}
    for primary_col, aliases in req_specs:
        found = _find_column(headers_map, aliases)
        if not found:
            raise ValueError(f"Kolom '{primary_col}' tidak ditemukan di file COGS")
        col_map[primary_col] = found

    # Optional columns
    cat_col = _find_column(headers_map, ["category", "kategori"])
    brand_col = _find_column(headers_map, ["brand", "merek"])
    supplier_col = _find_column(headers_map, ["supplier", "pemasok"])
    last_upd_col = _find_column(headers_map, ["last_updated", "updated_at", "tanggal"])

    parsed_rows: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for idx, r in enumerate(raw_rows, start=2):
        try:
            hpp = clean_int(r.get(col_map["hpp_per_unit"]))
        except Exception:
            warnings.append(f"Row {idx}: kolom 'hpp_per_unit' bukan angka ('{r.get(col_map['hpp_per_unit'])}'), row dilewati")
            continue

        cogs_row = {
            "sku": str(r.get(col_map["sku"], "")).strip(),
            "product_name": str(r.get(col_map["product_name"], "")).strip(),
            "category": str(r.get(cat_col, "")).strip() if cat_col else "",
            "brand": str(r.get(brand_col, "")).strip() if brand_col else "",
            "supplier": str(r.get(supplier_col, "")).strip() if supplier_col else "",
            "hpp_per_unit": hpp,
            "last_updated": str(r.get(last_upd_col, "")).strip() if last_upd_col and r.get(last_upd_col) else date.today().isoformat(),
        }
        parsed_rows.append(cogs_row)

    return parsed_rows, warnings


def parse_warehouse_inventory(file_content: bytes, filename: str = "") -> Tuple[Dict[str, int], List[str]]:
    """Parse master warehouse inventory tabular file into sku -> physical_stock dict."""
    raw_rows = read_tabular_rows(file_content, filename)
    if not raw_rows:
        return {}, []

    headers_map = {k.strip().lower(): k for k in raw_rows[0].keys()}

    sku_col = _find_column(headers_map, ["sku", "sku_reference_no", "seller_sku"])
    if not sku_col:
        raise ValueError("Kolom 'sku' tidak ditemukan di file Warehouse Inventory")

    stock_col = _find_column(headers_map, ["warehouse_physical_stock", "physical_stock", "current_stock", "stock"])
    if not stock_col:
        raise ValueError("Kolom 'warehouse_physical_stock' tidak ditemukan di file Warehouse Inventory")

    wh_dict: Dict[str, int] = {}
    warnings: List[str] = []

    for idx, r in enumerate(raw_rows, start=2):
        sku = str(r.get(sku_col, "")).strip()
        if not sku:
            continue
        try:
            stock = clean_int(r.get(stock_col))
            wh_dict[sku] = stock
        except Exception:
            warnings.append(f"Row {idx}: kolom 'warehouse_physical_stock' bukan angka ('{r.get(stock_col)}'), row dilewati")
            continue

    return wh_dict, warnings

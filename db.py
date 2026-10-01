import os
import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "cogs.db")


def get_db_path(db_path: Optional[str] = None) -> str:
    """Return explicit db_path if provided, else default instance path."""
    return db_path if db_path else DEFAULT_DB_PATH


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite database and create cogs table if it does not exist."""
    path = get_db_path(db_path)
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cogs (
            sku TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT DEFAULT '',
            brand TEXT DEFAULT '',
            supplier TEXT DEFAULT '',
            hpp_per_unit INTEGER NOT NULL,
            last_updated TEXT DEFAULT (date('now'))
        );
        """
    )
    conn.commit()
    conn.close()


def bulk_insert_cogs(rows: List[Dict[str, Any]], db_path: Optional[str] = None) -> int:
    """Bulk insert or replace COGS rows. Returns count of inserted rows."""
    if not rows:
        return 0

    path = get_db_path(db_path)
    init_db(path)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    count = 0
    for r in rows:
        sku = str(r.get("sku", "")).strip()
        if not sku:
            continue
        product_name = str(r.get("product_name", "")).strip()
        category = str(r.get("category", "")).strip()
        brand = str(r.get("brand", "")).strip()
        supplier = str(r.get("supplier", "")).strip()
        hpp = int(r.get("hpp_per_unit", 0))
        last_updated = r.get("last_updated") or date.today().isoformat()

        cursor.execute(
            """
            INSERT OR REPLACE INTO cogs (sku, product_name, category, brand, supplier, hpp_per_unit, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (sku, product_name, category, brand, supplier, hpp, last_updated),
        )
        count += 1

    conn.commit()
    conn.close()
    return count


def get_all_cogs(db_path: Optional[str] = None) -> Dict[str, int]:
    """Get all COGS as a dictionary mapping sku -> hpp_per_unit."""
    path = get_db_path(db_path)
    if not os.path.exists(path):
        return {}

    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT sku, hpp_per_unit FROM cogs")
        result = {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        result = {}
    finally:
        conn.close()
    return result


def get_all_cogs_dict(db_path: Optional[str] = None) -> Dict[str, int]:
    """Alias for get_all_cogs."""
    return get_all_cogs(db_path)


def get_all_cogs_rows(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all COGS as a list of dicts with all columns."""
    path = get_db_path(db_path)
    if not os.path.exists(path):
        return []

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT sku, product_name, category, brand, supplier, hpp_per_unit, last_updated FROM cogs ORDER BY sku ASC")
        rows = [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()
    return rows


def get_all_cogs_list(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Alias for get_all_cogs_rows."""
    return get_all_cogs_rows(db_path)


def get_cogs_by_sku(sku: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a single COGS row by SKU or None if not found."""
    path = get_db_path(db_path)
    if not os.path.exists(path):
        return None

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT sku, product_name, category, brand, supplier, hpp_per_unit, last_updated FROM cogs WHERE sku = ?",
            (sku,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()


def update_cogs(sku: str, hpp_per_unit: int, db_path: Optional[str] = None) -> bool:
    """Update hpp_per_unit for a single SKU. Preserves other columns."""
    path = get_db_path(db_path)
    if not os.path.exists(path):
        return False

    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE cogs SET hpp_per_unit = ?, last_updated = date('now') WHERE sku = ?",
            (int(hpp_per_unit), sku),
        )
        updated = cursor.rowcount > 0
        conn.commit()
    except sqlite3.OperationalError:
        updated = False
    finally:
        conn.close()
    return updated


def update_cogs_hpp(sku: str, hpp_per_unit: int, db_path: Optional[str] = None) -> bool:
    """Alias for update_cogs."""
    return update_cogs(sku, hpp_per_unit, db_path)


def delete_cogs(sku: str, db_path: Optional[str] = None) -> bool:
    """Delete a single SKU from cogs table."""
    path = get_db_path(db_path)
    if not os.path.exists(path):
        return False

    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM cogs WHERE sku = ?", (sku,))
        deleted = cursor.rowcount > 0
        conn.commit()
    except sqlite3.OperationalError:
        deleted = False
    finally:
        conn.close()
    return deleted


def delete_cogs_sku(sku: str, db_path: Optional[str] = None) -> bool:
    """Alias for delete_cogs."""
    return delete_cogs(sku, db_path)

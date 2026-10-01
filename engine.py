from datetime import datetime, timedelta
import math
from typing import Any, Dict, List, Optional, Tuple

MONTHS_ID = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def parse_dt(dt_val: Any) -> datetime:
    """Parse string or datetime object to datetime."""
    if isinstance(dt_val, datetime):
        return dt_val
    s = str(dt_val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.now()


def format_stockout_time(dt: datetime) -> str:
    """Format datetime as Indonesian date-time string e.g. '10 Okt 03:45'."""
    month_str = MONTHS_ID[dt.month] if 1 <= dt.month <= 12 else dt.strftime("%b")
    return f"{dt.day} {month_str} {dt.strftime('%H:%M')}"


def calculate_margins(
    orders: List[Dict[str, Any]],
    cogs: Dict[str, int],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Perform margin analysis for all orders against COGS HPP values.
    Returns (alerts, unmapped_skus).
    Sorted by level='negative' first (largest loss first), then others.
    """
    alerts: List[Dict[str, Any]] = []
    unmapped_skus: List[str] = []

    for order in orders:
        sku = order.get("sku", "")
        if sku not in cogs:
            if sku and sku not in unmapped_skus:
                unmapped_skus.append(sku)
            continue

        hpp = cogs[sku]
        actual_price = order.get("actual_unit_price", 0)
        margin = actual_price - hpp

        if margin < 0:
            level = "negative"
        elif margin < hpp * 0.2:
            level = "warning"
        else:
            level = "positive"

        alert = {
            "order_id": order.get("order_id", ""),
            "sku": sku,
            "product_name": order.get("product_name", ""),
            "channel": order.get("channel", ""),
            "original_price": order.get("original_price", 0),
            "actual_unit_price": actual_price,
            "hpp": hpp,
            "margin": margin,
            "level": level,
            "qty": order.get("qty", 1),
        }
        alerts.append(alert)

    # Sort: level=='negative' first with lowest margin (biggest loss) at top,
    # then other levels
    def sort_key(a: Dict[str, Any]) -> Tuple[int, int]:
        is_neg = 0 if a["level"] == "negative" else 1
        return (is_neg, a["margin"])

    alerts.sort(key=sort_key)
    return alerts, unmapped_skus


def calculate_budget(
    margin_alerts: List[Dict[str, Any]],
    campaign_budget: int,
) -> Dict[str, Any]:
    """
    Calculate campaign budget status and loss metrics.
    total_loss is sum of abs(margin) * qty for negative margin orders.
    """
    total_loss = sum(abs(a["margin"]) * a.get("qty", 1) for a in margin_alerts if a.get("margin", 0) < 0)

    if campaign_budget > 0:
        pct_used = (total_loss / campaign_budget) * 100.0
    else:
        pct_used = 0.0

    remaining = campaign_budget - total_loss

    if campaign_budget == 0 or pct_used <= 50.0:
        meter_level = "safe"
    elif pct_used <= 80.0:
        meter_level = "caution"
    else:
        meter_level = "over"

    return {
        "total_loss": total_loss,
        "campaign_budget": campaign_budget,
        "remaining": remaining,
        "pct_used": round(pct_used, 1),
        "meter_level": meter_level,
    }


def calculate_run_rate(
    orders: List[Dict[str, Any]],
    inventory: List[Dict[str, Any]],
    current_time: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Calculate hourly run rate and stockout prediction per (sku, channel).
    Only includes SKUs that appear in orders.
    """
    if current_time is None:
        current_time = datetime.now()

    # Build inventory lookup: (sku, channel) -> (channel_stock, product_name)
    inv_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for inv in inventory:
        key = (inv.get("sku", ""), inv.get("channel", ""))
        inv_map[key] = inv

    # Group orders by (sku, channel)
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for o in orders:
        sku = o.get("sku", "")
        channel = o.get("channel", "")
        if not sku or not channel:
            continue
        key = (sku, channel)
        if key not in groups:
            groups[key] = []
        groups[key].append(o)

    run_rates: List[Dict[str, Any]] = []

    for (sku, channel), ord_list in groups.items():
        total_sold = sum(o.get("qty", 0) for o in ord_list)

        # Find earliest order time
        order_times = [parse_dt(o["created_at"]) for o in ord_list if o.get("created_at")]
        earliest_time = min(order_times) if order_times else current_time

        hours_elapsed = (current_time - earliest_time).total_seconds() / 3600.0

        if hours_elapsed > 0 and total_sold > 0:
            run_rate_per_hour = total_sold / hours_elapsed
        else:
            run_rate_per_hour = 0.0

        # Retrieve inventory info
        inv_item = inv_map.get((sku, channel))
        channel_stock = inv_item.get("channel_stock", 0) if inv_item else 0
        product_name = (
            inv_item.get("product_name")
            if inv_item and inv_item.get("product_name")
            else ord_list[0].get("product_name", sku)
        )

        # Stockout calculation
        if channel_stock == 0:
            hours_until_stockout = 0.0
            stockout_time = format_stockout_time(current_time)
            level = "negative"
        elif run_rate_per_hour > 0:
            hours_until_stockout = channel_stock / run_rate_per_hour
            pred_dt = current_time + timedelta(hours=hours_until_stockout)
            stockout_time = format_stockout_time(pred_dt)

            if hours_until_stockout < 2.0:
                level = "negative"
            elif hours_until_stockout < 6.0:
                level = "warning"
            else:
                level = "positive"
        else:
            hours_until_stockout = float("inf")
            stockout_time = None
            level = "positive"

        row = {
            "sku": sku,
            "product_name": product_name,
            "channel": channel,
            "total_sold": total_sold,
            "hours_elapsed": round(hours_elapsed, 1),
            "run_rate_per_hour": round(run_rate_per_hour, 1),
            "channel_stock": channel_stock,
            "hours_until_stockout": hours_until_stockout,
            "stockout_time": stockout_time,
            "level": level,
        }
        run_rates.append(row)

    # Sort: hours_until_stockout ascending (infinity at the bottom)
    def sort_key(r: Dict[str, Any]) -> float:
        val = r["hours_until_stockout"]
        return float("inf") if math.isinf(val) else val

    run_rates.sort(key=sort_key)
    return run_rates


def calculate_rebalance(
    inventory: List[Dict[str, Any]],
    warehouse: Dict[str, int],
) -> List[Dict[str, Any]]:
    """
    Detect SKUs with starved marketplace channel stock (<= 5) while warehouse has ample stock (> 50).
    Returns list of RebalanceRow where level == 'warning', sorted by warehouse_stock descending.
    """
    # Map inventory by sku -> {channel: stock, product_name: name}
    sku_inv: Dict[str, Dict[str, Any]] = {}
    for inv in inventory:
        sku = inv.get("sku", "")
        if not sku:
            continue
        if sku not in sku_inv:
            sku_inv[sku] = {"shopee": 0, "tiktok": 0, "product_name": inv.get("product_name", sku)}
        channel = inv.get("channel", "")
        if channel in ("shopee", "tiktok"):
            sku_inv[sku][channel] = inv.get("channel_stock", 0)
        if inv.get("product_name") and not sku_inv[sku]["product_name"]:
            sku_inv[sku]["product_name"] = inv.get("product_name")

    rebalance_rows: List[Dict[str, Any]] = []

    for sku, wh_stock in warehouse.items():
        if wh_stock <= 50:
            continue

        inv_data = sku_inv.get(sku, {"shopee": 0, "tiktok": 0, "product_name": sku})
        shopee_stock = inv_data.get("shopee", 0)
        tiktok_stock = inv_data.get("tiktok", 0)
        product_name = inv_data.get("product_name", sku)

        needs_rebalance = shopee_stock <= 5 or tiktok_stock <= 5
        if not needs_rebalance:
            continue

        transfer_qty = min(100, wh_stock // 2)
        recommendations = []
        if shopee_stock <= 5:
            recommendations.append(f"Replenish Shopee (+{transfer_qty} unit)")
        if tiktok_stock <= 5:
            recommendations.append(f"Replenish TikTok (+{transfer_qty} unit)")

        row = {
            "sku": sku,
            "product_name": product_name,
            "warehouse_stock": wh_stock,
            "shopee_stock": shopee_stock,
            "tiktok_stock": tiktok_stock,
            "level": "warning",
            "recommendations": recommendations,
        }
        rebalance_rows.append(row)

    # Sort by warehouse_stock descending
    rebalance_rows.sort(key=lambda r: r["warehouse_stock"], reverse=True)
    return rebalance_rows

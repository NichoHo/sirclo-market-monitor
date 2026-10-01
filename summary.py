from datetime import datetime
from typing import Any, Dict, List, Optional


def format_rupiah(val: int) -> str:
    """Format an integer as Indonesian Rupiah string (e.g. 5000000 -> 'Rp 5.000.000')."""
    return f"Rp {val:,.0f}".replace(",", ".")


def generate_alert_copy_text(alert: Dict[str, Any]) -> str:
    """Generate single-item alert copy text for WhatsApp."""
    sku = alert.get("sku", "")
    product_name = alert.get("product_name", "")
    margin = alert.get("margin", 0)
    channel = alert.get("channel", "")
    actual = alert.get("actual_unit_price", 0)
    hpp = alert.get("hpp", 0)

    # e.g. -19503
    margin_str = f"{margin}" if margin < 0 else f"-{margin}"

    return (
        f"ALERT: {sku} ({product_name}) jual rugi {margin_str}/unit di {channel}. "
        f"Harga jual Rp {actual}, HPP Rp {hpp}. Segera cek voucher."
    )


def generate_summary_text(
    margin_alerts: List[Dict[str, Any]],
    budget_status: Dict[str, Any],
    run_rate: List[Dict[str, Any]],
    rebalance: List[Dict[str, Any]],
    campaign_name: str = "10.10 Midnight Mega Sale",
    current_datetime: Optional[str] = None,
) -> str:
    """
    Generate complete plain-text WhatsApp summary report.
    Conforms to TECH_SPEC.md Section 7 and AC 8.
    """
    if current_datetime is None:
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M")

    total_loss = budget_status.get("total_loss", 0)
    budget = budget_status.get("campaign_budget", 0)
    pct = budget_status.get("pct_used", 0.0)
    meter_level = budget_status.get("meter_level", "safe")

    status_map = {
        "safe": "AMAN",
        "caution": "WASPADA",
        "over": "OVER BUDGET",
    }
    status_label = status_map.get(meter_level, meter_level.upper())
    pct_formatted = f"{int(pct)}" if pct == int(pct) else f"{pct:.1f}"

    # Filter negative margin alerts
    neg_alerts = [a for a in margin_alerts if a.get("level") == "negative" or a.get("margin", 0) < 0]

    # Filter critical stockout SKUs (level == 'negative' or hours < 2)
    crit_skus = [
        r
        for r in run_rate
        if r.get("level") == "negative"
        or (isinstance(r.get("hours_until_stockout"), (int, float)) and r.get("hours_until_stockout", 999) < 2.0)
    ]

    # Rebalance items
    rebalance_items = [r for r in rebalance if r.get("level") == "warning"]
    if not rebalance_items and rebalance:
        rebalance_items = rebalance

    lines = [
        "RINGKASAN MARKETPLACE MONITOR",
        f"Campaign: {campaign_name}",
        f"Waktu: {current_datetime}",
        "=============================",
        "",
        f"BUDGET: {format_rupiah(total_loss)} / {format_rupiah(budget)} ({pct_formatted}% terpakai) — {status_label}",
        "",
        f"ALERT JUAL RUGI ({len(neg_alerts)} order)",
    ]

    for item in neg_alerts:
        loss = abs(item.get("margin", 0))
        lines.append(f"- {item.get('sku')} | {item.get('channel')} | Rugi {format_rupiah(loss)}/unit")

    lines.append("")
    lines.append(f"PREDIKSI HABIS ({len(crit_skus)} SKU kritis)")
    for r in crit_skus:
        hrs = r.get("hours_until_stockout", 0)
        hrs_str = f"{int(hrs)}" if hrs == int(hrs) else f"{hrs:.1f}"
        lines.append(f"- {r.get('sku')} | {r.get('channel')} | Habis ~{r.get('stockout_time', '-')} ({hrs_str}j lagi)")

    lines.append("")
    lines.append(f"PERLU REPLENISH ({len(rebalance_items)} SKU)")
    for reb in rebalance_items:
        lines.append(
            f"- {reb.get('sku')} | Gudang: {reb.get('warehouse_stock', 0)} | "
            f"Shopee: {reb.get('shopee_stock', 0)} | TikTok: {reb.get('tiktok_stock', 0)}"
        )

    return "\n".join(lines)

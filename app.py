import io
import os
from datetime import datetime
from flask import Flask, jsonify, render_template, request

from db import (
    DEFAULT_DB_PATH,
    get_db_path,
    init_db,
    bulk_insert_cogs,
    get_all_cogs,
    get_all_cogs_rows,
    get_cogs_by_sku,
    update_cogs,
    delete_cogs,
)
from engine import (
    calculate_margins,
    calculate_budget,
    calculate_run_rate,
    calculate_rebalance,
    parse_dt,
)
from parser import (
    clean_int,
    parse_shopee_orders,
    parse_tiktok_orders,
    parse_shopee_inventory,
    parse_tiktok_inventory,
    parse_cogs_csv,
    parse_warehouse_inventory,
)
from summary import generate_summary_text
from guardrails import (
    rate_limit,
    concurrent_guard,
    reset_rate_limits,
    reset_in_flight_locks,
)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.urandom(24)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

# Ensure default database directory and table exist
try:
    init_db(get_current_db_path())
except Exception:
    pass


@app.after_request
def cleanup_uploaded_files(response):
    try:
        if "files" in request.__dict__:
            for key in request.files:
                for f in request.files.getlist(key):
                    try:
                        f.close()
                    except Exception:
                        pass
    except Exception:
        pass
    return response


def get_current_db_path() -> str:
    """Return configured database path or default instance path."""
    return app.config.get("DB_PATH", get_db_path())


def load_warehouse_inventory(uploaded_file=None):
    """Load warehouse inventory from uploaded file or fall back to default simulation CSV."""
    if uploaded_file and uploaded_file.filename:
        return parse_warehouse_inventory(uploaded_file.read(), uploaded_file.filename)

    default_path = os.path.join(os.path.dirname(__file__), "data", "master_warehouse_inventory_cogs.csv")
    if os.path.exists(default_path):
        with open(default_path, "rb") as wf:
            return parse_warehouse_inventory(wf.read(), "master_warehouse_inventory_cogs.csv")
    return {}, []


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "error": "Ukuran file terlalu besar. Total file yang diunggah tidak boleh melebihi 16 MB."
    }), 413


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/cogs/upload", methods=["POST"])
@rate_limit(limit=10, window=60, bucket="cogs_upload")
def upload_cogs():
    if "cogs_file" not in request.files or not request.files["cogs_file"].filename:
        return jsonify({"error": "Field 'cogs_file' wajib diunggah"}), 400

    f = request.files["cogs_file"]
    content = f.read()
    if not content:
        return jsonify({"error": "File COGS kosong"}), 400

    try:
        parsed_rows, warnings = parse_cogs_csv(content, f.filename)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Gagal membaca file COGS: {str(e)}"}), 400

    db_path = get_current_db_path()
    inserted = bulk_insert_cogs(parsed_rows, db_path)
    return jsonify({
        "inserted": inserted,
        "message": f"{inserted} SKU berhasil disimpan",
    }), 200


@app.route("/api/cogs", methods=["GET"])
@rate_limit(limit=60, window=60, bucket="cogs_list")
def list_cogs():
    db_path = get_current_db_path()
    rows = get_all_cogs_rows(db_path)
    return jsonify({
        "data": rows,
        "count": len(rows),
    }), 200


@app.route("/api/cogs/<sku>", methods=["PUT"])
@rate_limit(limit=30, window=60, bucket="cogs_mutation")
def update_cogs_endpoint(sku):
    data = request.get_json(silent=True)
    if not data or "hpp_per_unit" not in data:
        return jsonify({"error": "Field 'hpp_per_unit' wajib diisi"}), 400

    val = data["hpp_per_unit"]
    if not isinstance(val, (int, float)) or isinstance(val, bool):
        return jsonify({"error": "Nilai 'hpp_per_unit' harus berupa angka bulat"}), 400

    try:
        hpp = int(val)
        if hpp < 0:
            return jsonify({"error": "Nilai 'hpp_per_unit' tidak boleh negatif"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Nilai 'hpp_per_unit' harus berupa angka bulat"}), 400

    db_path = get_current_db_path()
    existing = get_cogs_by_sku(sku, db_path)
    if not existing:
        return jsonify({"error": f"SKU '{sku}' tidak ditemukan"}), 404

    update_cogs(sku, hpp, db_path)
    return jsonify({
        "sku": sku,
        "hpp_per_unit": hpp,
        "message": "HPP berhasil diupdate",
    }), 200


@app.route("/api/cogs/<sku>", methods=["DELETE"])
@rate_limit(limit=30, window=60, bucket="cogs_mutation")
def delete_cogs_endpoint(sku):
    db_path = get_current_db_path()
    delete_cogs(sku, db_path)
    return jsonify({
        "message": f"{sku} berhasil dihapus",
    }), 200


@app.route("/api/analyze", methods=["POST"])
@rate_limit(limit=10, window=60, bucket="analyze")
@concurrent_guard(endpoint="analyze")
def analyze():
    required_files = ["shopee_orders", "tiktok_orders", "shopee_inventory", "tiktok_inventory"]
    for rf in required_files:
        if rf not in request.files or not request.files[rf].filename:
            return jsonify({"error": f"Kolom file '{rf}' wajib diunggah"}), 400

    if "campaign_budget" not in request.form:
        return jsonify({"error": "Parameter 'campaign_budget' wajib diisi"}), 400

    budget_raw = request.form.get("campaign_budget")
    try:
        campaign_budget = clean_int(budget_raw)
        if campaign_budget < 0:
            return jsonify({"error": "Parameter 'campaign_budget' tidak boleh negatif"}), 400
        if campaign_budget > 1_000_000_000_000:
            return jsonify({"error": "Parameter 'campaign_budget' melebihi batas maksimal Rp 1.000.000.000.000"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Parameter 'campaign_budget' harus berupa angka"}), 400

    # Parse order and inventory files
    try:
        sp_orders_file = request.files["shopee_orders"]
        sp_orders, sp_o_warn = parse_shopee_orders(sp_orders_file.read(), sp_orders_file.filename)

        tt_orders_file = request.files["tiktok_orders"]
        tt_orders, tt_o_warn = parse_tiktok_orders(tt_orders_file.read(), tt_orders_file.filename)

        sp_inv_file = request.files["shopee_inventory"]
        sp_inv, sp_i_warn = parse_shopee_inventory(sp_inv_file.read(), sp_inv_file.filename)

        tt_inv_file = request.files["tiktok_inventory"]
        tt_inv, tt_i_warn = parse_tiktok_inventory(tt_inv_file.read(), tt_inv_file.filename)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Gagal membaca file: {str(e)}"}), 400

    warnings = []
    warnings.extend(sp_o_warn)
    warnings.extend(tt_o_warn)
    warnings.extend(sp_i_warn)
    warnings.extend(tt_i_warn)

    db_path = get_current_db_path()
    cogs = get_all_cogs(db_path)

    wh_file = request.files.get("warehouse_inventory")
    wh_dict, wh_warn = load_warehouse_inventory(wh_file)
    warnings.extend(wh_warn)

    orders = sp_orders + tt_orders
    inventory = sp_inv + tt_inv

    # Determine reference current_time for run_rate
    current_time = None
    if orders:
        valid_times = [parse_dt(o["created_at"]) for o in orders if o.get("created_at")]
        if valid_times:
            max_time = max(valid_times)
            now = datetime.now()
            if now < max_time or (now - max_time).days > 30:
                current_time = max_time
            else:
                current_time = now

    margin_alerts, unmapped_skus = calculate_margins(orders, cogs)
    budget_status = calculate_budget(margin_alerts, campaign_budget)
    run_rate = calculate_run_rate(orders, inventory, current_time=current_time)
    rebalance = calculate_rebalance(inventory, wh_dict)

    campaign_name = request.form.get("campaign_name", "10.10 Midnight Mega Sale")
    summary_text = generate_summary_text(
        margin_alerts=margin_alerts,
        budget_status=budget_status,
        run_rate=run_rate,
        rebalance=rebalance,
        campaign_name=campaign_name,
    )

    return jsonify({
        "margin_alerts": margin_alerts,
        "budget_status": budget_status,
        "run_rate": run_rate,
        "rebalance": rebalance,
        "unmapped_skus": unmapped_skus,
        "warnings": warnings,
        "summary_text": summary_text,
    }), 200


@app.route("/api/sample-data", methods=["GET"])
@rate_limit(limit=20, window=60, bucket="sample_data")
def sample_data():
    db_path = get_current_db_path()
    cogs = get_all_cogs(db_path)

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    cogs_path = os.path.join(data_dir, "internal_cogs_hpp.csv")

    # If COGS is empty or incomplete, auto-seed from internal_cogs_hpp.csv
    if len(cogs) < 50 and os.path.exists(cogs_path):
        with open(cogs_path, "rb") as cf:
            parsed_cogs, _ = parse_cogs_csv(cf.read(), "internal_cogs_hpp.csv")
            bulk_insert_cogs(parsed_cogs, db_path)
            cogs = get_all_cogs(db_path)

    warnings = []

    # Read simulation CSVs
    sp_orders_path = os.path.join(data_dir, "shopee_orders.csv")
    with open(sp_orders_path, "rb") as f:
        sp_orders, sp_warn = parse_shopee_orders(f.read(), "shopee_orders.csv")
    warnings.extend(sp_warn)

    tt_orders_path = os.path.join(data_dir, "tiktok_orders.csv")
    with open(tt_orders_path, "rb") as f:
        tt_orders, tt_warn = parse_tiktok_orders(f.read(), "tiktok_orders.csv")
    warnings.extend(tt_warn)

    sp_inv_path = os.path.join(data_dir, "shopee_inventory.csv")
    with open(sp_inv_path, "rb") as f:
        sp_inv, sp_i_warn = parse_shopee_inventory(f.read(), "shopee_inventory.csv")
    warnings.extend(sp_i_warn)

    tt_inv_path = os.path.join(data_dir, "tiktok_inventory.csv")
    with open(tt_inv_path, "rb") as f:
        tt_inv, tt_i_warn = parse_tiktok_inventory(f.read(), "tiktok_inventory.csv")
    warnings.extend(tt_i_warn)

    wh_path = os.path.join(data_dir, "master_warehouse_inventory_cogs.csv")
    wh_dict = {}
    if os.path.exists(wh_path):
        with open(wh_path, "rb") as f:
            wh_dict, wh_warn = parse_warehouse_inventory(f.read(), "master_warehouse_inventory_cogs.csv")
            warnings.extend(wh_warn)

    orders = sp_orders + tt_orders
    inventory = sp_inv + tt_inv

    # Hardcoded campaign_budget 5,000,000 for sample data demo
    campaign_budget = 5000000

    current_time = None
    if orders:
        valid_times = [parse_dt(o["created_at"]) for o in orders if o.get("created_at")]
        if valid_times:
            max_time = max(valid_times)
            now = datetime.now()
            if now < max_time or (now - max_time).days > 30:
                current_time = max_time
            else:
                current_time = now

    margin_alerts, unmapped_skus = calculate_margins(orders, cogs)
    budget_status = calculate_budget(margin_alerts, campaign_budget)
    run_rate = calculate_run_rate(orders, inventory, current_time=current_time)
    rebalance = calculate_rebalance(inventory, wh_dict)

    summary_text = generate_summary_text(
        margin_alerts=margin_alerts,
        budget_status=budget_status,
        run_rate=run_rate,
        rebalance=rebalance,
        campaign_name="10.10 Midnight Mega Sale",
    )

    return jsonify({
        "margin_alerts": margin_alerts,
        "budget_status": budget_status,
        "run_rate": run_rate,
        "rebalance": rebalance,
        "unmapped_skus": unmapped_skus,
        "warnings": warnings,
        "summary_text": summary_text,
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

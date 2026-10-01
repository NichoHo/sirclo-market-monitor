# SIRCLO Training - Simulation Data: Mega-Sale Fire Drill

This dataset simulates the operational data during a midnight Double-Day Mega Campaign (10.10) for 4 beauty & fashion brand stores managed across **Shopee** and **TikTok Shop**, directly modeling the bottlenecks identified in the problem statement.

---

## 1. Files Overview

| File Path | Description | Records | Key Purpose |
|---|---|---|---|
| [`data/shopee_orders.csv`](file:///c:/Users/Nicholas%20Ho/Documents/Programming/Project/SIRCLO%20Training/data/shopee_orders.csv) | Shopee Seller Centre Order Export | 50 Orders | Identify stacked vouchers selling below COGS |
| [`data/tiktok_orders.csv`](file:///c:/Users/Nicholas%20Ho/Documents/Programming/Project/SIRCLO%20Training/data/tiktok_orders.csv) | TikTok Shop Seller Center Order List | 50 Orders | Identify stacked coupons selling below COGS |
| [`data/shopee_inventory.csv`](file:///c:/Users/Nicholas%20Ho/Documents/Programming/Project/SIRCLO%20Training/data/shopee_inventory.csv) | Shopee Stock Export | 50 SKUs | Channel allocated stock vs stockout status |
| [`data/tiktok_inventory.csv`](file:///c:/Users/Nicholas%20Ho/Documents/Programming/Project/SIRCLO%20Training/data/tiktok_inventory.csv) | TikTok Shop Stock Export | 50 SKUs | Channel allocated stock vs stockout status |
| [`data/master_warehouse_inventory_cogs.csv`](file:///c:/Users/Nicholas%20Ho/Documents/Programming/Project/SIRCLO%20Training/data/master_warehouse_inventory_cogs.csv) | Internal Master Catalog & Warehouse Inventory | 50 SKUs | Benchmark for COGS & central warehouse physical stock |

> **Format File yang Didukung**: File simulasi pada direktori ini disediakan dalam format CSV. Namun, sistem aplikasi dirancang fleksibel untuk menerima file tabular serupa seperti Excel (`.xlsx`, `.xls`) dan TSV (`.tsv`). Pengguna dapat mengunggah file ekspor langsung dari Seller Centre tanpa perlu mengonversi file secara manual.

---

## 2. Key Problem Scenarios Simulated

### A. The Voucher Stacking Trap (Selling Below COGS)
- **Problem**: Flash sale/deal discounts and store vouchers stack simultaneously.
- **Example in Data (`shopee_orders.csv`)**:
  - `Order ID`: `261010SP0007`
  - `Product`: Dewy Tint Lip Glaze - Nude Peach (`SKU-LIP-GLAZE-01`)
  - `Normal Price`: Rp 115,000 | `COGS`: Rp 55,000
  - `Deal Price`: Rp 85,497 | `Seller Voucher`: Rp 40,000 | `Seller Rebate`: Rp 10,000
  - `Real Selling Price Per Unit`: **Rp 35,497**
  - **Result**: Net loss of **-Rp 19,503 per unit** (selling strictly below COGS).

### B. The Hero SKU Stockout Mismatch
- **Problem**: Fixed allocated inventory causes hero SKUs to go out-of-stock on fast-selling channels while inventory sits idle in the warehouse and other channels.
- **Example in Data**:
  - `Product`: Velvet Matte Lipstick - Dusky Rose (`SKU-LIP-VELVET-01`)
  - `Central Warehouse Physical Stock`: **500 units**
  - `Shopee Available Stock`: **0 units (OUT OF STOCK)** — Missing midnight sales!
  - `TikTok Available Stock`: **29 units (IN STOCK)**

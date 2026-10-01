# TECH_SPEC.md — Data Contracts, Logic & Edge Cases
> SIRCLO Marketplace Monitor

Dokumen ini ditulis untuk dikonsumsi oleh AI model yang akan mengimplementasikan project. Semua kontrak bersifat exact — ikuti persis.

Baca juga sebelum implementasi:
- `PRODUCT_SPEC.md` — user journey, UX states, acceptance criteria
- `design.md` — exact UI tokens (warna, font, spacing, komponen)
- `learnings.md` — akumulasi konteks, status pengerjaan, keputusan teknis & handover antar sesi AI

---

## 1. Architecture

### Stack

| Layer | Technology | Alasan |
|---|---|---|
| Backend | Python 3.10+ / Flask | Ringan, standard library CSV + openpyxl untuk Excel (.xlsx/.xls), mudah deploy |
| Frontend | Single HTML + vanilla JS + CSS | Tidak perlu build step, npm, atau bundler |
| Persistence | SQLite (via `sqlite3` stdlib) | COGS data persist tanpa setup database server |
| Font | Google Fonts (Inter, JetBrains Mono) | Loaded via CDN `<link>` tag |

### Constraints

- TIDAK ada npm, webpack, atau build tools
- TIDAK ada React, Vue, atau framework JS
- TIDAK ada database server (PostgreSQL, MySQL, dll.)
- TIDAK ada authentication / login
- TIDAK ada environment variables yang wajib
- Semua berjalan dengan `python app.py` → buka `http://localhost:5000`

### File Structure

```
project_root/
├── app.py                    # Flask application (entry point)
├── db.py                     # SQLite helper (init, COGS CRUD)
├── engine.py                 # Semua calculation logic
├── parser.py                 # Multi-format tabular file parser (CSV, Excel .xlsx/.xls, TSV) & validation
├── summary.py                # WhatsApp summary & card copy text generator
├── guardrails.py             # In-memory rate limiter, concurrent request guard & resilience helpers
├── learnings.md              # Log akumulasi konteks, progress, catatan bug & handover antar sesi AI
├── instance/
│   └── cogs.db               # SQLite database (auto-created)
├── static/
│   ├── style.css             # Semua CSS (token dari design.md)
│   └── app.js                # Semua client-side JS
├── templates/
│   └── index.html            # Single page template (Jinja2)
├── data/                     # Sample/simulation datasets (CSV, Excel, etc.)
│   ├── shopee_orders.csv
│   ├── tiktok_orders.csv
│   ├── shopee_inventory.csv
│   ├── tiktok_inventory.csv
│   ├── internal_cogs_hpp.csv
│   └── master_warehouse_inventory_cogs.csv
├── PRODUCT_SPEC.md
├── TECH_SPEC.md
└── design.md
```

### AI Session Continuity Protocol (`learnings.md`)

Karena implementasi project ini dapat dikerjakan secara bertahap oleh beberapa sesi AI (Antigravity) yang berbeda, file `learnings.md` bertindak sebagai **living memory** dan single source of truth untuk mentransfer konteks, status pekerjaan, keputusan teknis, dan pembelajaran/gotchas antar sesi.

#### Aturan untuk Setiap Sesi AI:
1. **Awal Sesi (Session Start / Onboarding)**:
   - Wajib membaca `learnings.md` bersamaan dengan `PRODUCT_SPEC.md`, `TECH_SPEC.md`, dan `design.md`.
   - Periksa ringkasan status terakhir, item yang telah diselesaikan sesi sebelumnya, dan daftar **Next Steps**.
   - Verifikasi status kode dan tes yang relevan sebelum melanjutkan pekerjaan.

2. **Selama Sesi (During Session)**:
   - Apabila menemukan kejanggalan format data, batasan pustaka, keputusan teknis non-trivial, atau solusi bug tertentu, catat insight tersebut.

3. **Akhir Sesi (Session Wrap-up / Handover)**:
   - Sebelum sesi diakhiri, perbarui `learnings.md` dengan entri baru yang mencakup:
     - **Tasks Completed**: Daftar deliverable/fungsi yang berhasil dibuat dan test cases yang lolos.
     - **Key Decisions**: Keputusan implementasi atau alasan teknis spesifik (mengapa suatu pendekatan dipilih).
     - **Gotchas & Learnings**: Edge cases, bug, atau catatan penting yang perlu diketahui sesi berikutnya (misal: quirk encoding CSV, formatting Rupiah, skenario division by zero, dll.).
     - **Next Steps**: Panduan aksi konkret yang belum terselesaikan untuk dilanjutkan oleh sesi AI berikutnya.

---

## 2. Data Schemas

### 2.1 Input Schemas (CSV, Excel, TSV)

Setiap file input (baik berupa CSV, Excel `.xlsx`/`.xls`, maupun TSV) memiliki header kolom yang berbeda tergantung marketplace. Parser membaca baris pertama atau lembar kerja pertama (*active/first sheet*) dan memetakan kolom ke schema internal yang seragam.

#### Shopee Orders (`shopee_orders.csv` / `.xlsx`)

| Column Name (CSV/Excel) | Type | Required | Map ke Internal |
|---|---|---|---|
| `order_id` | string | yes | `order_id` |
| `order_creation_time` | string (datetime) | yes | `created_at` |
| `order_status` | string | yes | `status` |
| `sku_reference_no` | string | yes | `sku` |
| `product_name` | string | yes | `product_name` |
| `quantity` | int | yes | `qty` |
| `original_price` | int | yes | `original_price` |
| `deal_price` | int | no | — |
| `seller_voucher_discount` | int | no | — |
| `seller_rebate` | int | no | — |
| `shopee_voucher_subsidy` | int | no | — |
| `seller_absorbed_discount_total` | int | no | — |
| `real_selling_price_per_unit` | int | yes | `actual_unit_price` |
| `buyer_total_payment` | int | no | — |

#### TikTok Orders (`tiktok_orders.csv` / `.xlsx`)

| Column Name (CSV/Excel) | Type | Required | Map ke Internal |
|---|---|---|---|
| `order_id` | string | yes | `order_id` |
| `created_time` | string (datetime) | yes | `created_at` |
| `order_status` | string | yes | `status` |
| `seller_sku` | string | yes | `sku` |
| `product_name` | string | yes | `product_name` |
| `quantity` | int | yes | `qty` |
| `retail_price` | int | yes | `original_price` |
| `seller_discount` | int | no | — |
| `shop_voucher_discount` | int | no | — |
| `platform_discount` | int | no | — |
| `platform_voucher` | int | no | — |
| `seller_absorbed_discount_total` | int | no | — |
| `net_unit_settlement_price` | int | yes | `actual_unit_price` |
| `total_settlement_amount` | int | no | — |

#### Shopee Inventory (`shopee_inventory.csv` / `.xlsx`)

| Column Name (CSV/Excel) | Type | Required | Map ke Internal |
|---|---|---|---|
| `sku_reference_no` | string | yes | `sku` |
| `product_name` | string | yes | `product_name` |
| `current_stock` | int | yes | `channel_stock` |
| `stock_status` | string | no | — |

#### TikTok Inventory (`tiktok_inventory.csv` / `.xlsx`)

| Column Name (CSV/Excel) | Type | Required | Map ke Internal |
|---|---|---|---|
| `seller_sku` | string | yes | `sku` |
| `product_name` | string | yes | `product_name` |
| `available_stock` | int | yes | `channel_stock` |
| `inventory_status` | string | no | — |

### 2.2 Internal Unified Schema

Setelah parsing, semua data dikonversi ke schema internal berikut.

#### OrderRow

```python
{
    "order_id": str,
    "created_at": str,       # ISO format "2026-10-10 00:07:37"
    "sku": str,
    "product_name": str,
    "qty": int,
    "original_price": int,   # Harga normal per unit (Rupiah)
    "actual_unit_price": int, # Harga jual aktual per unit setelah semua diskon
    "channel": str,          # "shopee" atau "tiktok"
}
```

#### InventoryRow

```python
{
    "sku": str,
    "product_name": str,
    "channel_stock": int,
    "channel": str,          # "shopee" atau "tiktok"
}
```

#### COGSRow (dari SQLite)

```python
{
    "sku": str,
    "product_name": str,
    "category": str,
    "brand": str,
    "supplier": str,
    "hpp_per_unit": int,     # Harga Pokok Penjualan per unit (Rupiah)
    "last_updated": str,     # ISO date "2026-10-01"
}
```

---

## 3. SQLite Schema

Database file: `instance/cogs.db` (auto-created saat pertama kali `app.py` dijalankan).

### Table: `cogs`

```sql
CREATE TABLE IF NOT EXISTS cogs (
    sku TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT DEFAULT '',
    brand TEXT DEFAULT '',
    supplier TEXT DEFAULT '',
    hpp_per_unit INTEGER NOT NULL,
    last_updated TEXT DEFAULT (date('now'))
);
```

### Operations

| Operation | Kapan |
|---|---|
| `INSERT OR REPLACE` bulk | Upload file COGS (CSV, Excel `.xlsx`/`.xls`, TSV) pertama kali |
| `SELECT *` | Setiap kali analisis dijalankan |
| `UPDATE ... WHERE sku = ?` | Operator edit HPP satu SKU |
| `DELETE WHERE sku = ?` | Operator hapus SKU |

---

## 4. Calculation Engine (`engine.py`)

Semua fungsi menerima list of dicts dan mengembalikan list of dicts. Tidak ada side effects.

### 4.1 Margin Analysis (Alert Jual Rugi)

**Input**: `orders: list[OrderRow]`, `cogs: dict[str, int]` (sku → hpp_per_unit)

**Output**: `list[MarginAlert]`

```python
# Untuk setiap order:
margin = order["actual_unit_price"] - cogs[order["sku"]]

# Classification:
if margin < 0:
    level = "negative"       # Jual rugi
elif margin < hpp * 0.2:
    level = "warning"        # Margin tipis (< 20% dari HPP)
else:
    level = "positive"       # Aman

# MarginAlert shape:
{
    "order_id": str,
    "sku": str,
    "product_name": str,
    "channel": str,           # "shopee" / "tiktok"
    "original_price": int,
    "actual_unit_price": int,
    "hpp": int,
    "margin": int,            # Bisa negatif
    "level": str,             # "negative" / "warning" / "positive"
}
```

**Sort**: `level == "negative"` dulu, lalu by `margin` ascending (kerugian terbesar di atas).

**Edge case**: Jika SKU tidak ada di `cogs` dict, SKIP order tersebut dan masukkan SKU ke list `unmapped_skus`. Jangan crash.

### 4.2 Budget Safe

**Input**: `margin_alerts: list[MarginAlert]`, `campaign_budget: int`

**Output**: `BudgetStatus`

```python
# Total kerugian = sum semua margin negatif (diubah ke positif)
total_loss = sum(abs(a["margin"]) * order_qty for a in margin_alerts if a["margin"] < 0)

# Catatan: kalikan dengan qty dari order asli
# Harus pass qty info ke margin_alerts atau hitung dari orders langsung

pct_used = (total_loss / campaign_budget) * 100 if campaign_budget > 0 else 0

if pct_used <= 50:
    meter_level = "safe"
elif pct_used <= 80:
    meter_level = "caution"
else:
    meter_level = "over"

# BudgetStatus shape:
{
    "total_loss": int,
    "campaign_budget": int,
    "remaining": int,         # campaign_budget - total_loss (bisa negatif)
    "pct_used": float,        # 0.0 - 100.0+
    "meter_level": str,       # "safe" / "caution" / "over"
}
```

**Edge case**: `campaign_budget == 0` → `pct_used = 0`, `meter_level = "safe"`. Jangan divide by zero.

### 4.3 Run Rate & Stockout Prediction

**Input**: `orders: list[OrderRow]`, `inventory: list[InventoryRow]`, `current_time: datetime`

**Output**: `list[RunRateRow]`

```python
# Group orders by (sku, channel)
# Untuk setiap group:

total_qty_sold = sum(order["qty"] for order in group)

# Cari waktu order paling awal di group
earliest_order_time = min(parse(order["created_at"]) for order in group)

# Jam berjalan
hours_elapsed = (current_time - earliest_order_time).total_seconds() / 3600.0

# Run rate
if hours_elapsed > 0:
    run_rate_per_hour = total_qty_sold / hours_elapsed
else:
    run_rate_per_hour = 0

# Prediksi habis
channel_stock = inventory_lookup(sku, channel)  # dari inventory data

if run_rate_per_hour > 0:
    hours_until_stockout = channel_stock / run_rate_per_hour
    stockout_time = current_time + timedelta(hours=hours_until_stockout)
else:
    hours_until_stockout = float('inf')
    stockout_time = None  # Tampilkan "∞"

# Classification
if hours_until_stockout < 2:
    level = "negative"       # Kritis
elif hours_until_stockout < 6:
    level = "warning"        # Perlu perhatian
else:
    level = "positive"       # Aman

# RunRateRow shape:
{
    "sku": str,
    "product_name": str,
    "channel": str,
    "total_sold": int,
    "hours_elapsed": float,   # Dibulatkan 1 desimal
    "run_rate_per_hour": float, # Dibulatkan 1 desimal
    "channel_stock": int,
    "hours_until_stockout": float,  # Atau float('inf')
    "stockout_time": str | None,    # "10 Okt 03:45" atau None
    "level": str,
}
```

**Sort**: `hours_until_stockout` ascending (paling cepat habis di atas). `inf` di paling bawah.

**Edge cases**:
- `run_rate_per_hour == 0` → `hours_until_stockout = inf`, `stockout_time = None`. Tampilkan "∞" di UI.
- `channel_stock == 0` → `hours_until_stockout = 0`, level `"negative"`. Sudah habis.
- SKU ada di inventory tapi tidak ada di orders → tidak muncul di run rate (belum ada penjualan, tidak bisa hitung velocity).

### 4.4 Stock Rebalancing

**Input**: `inventory: list[InventoryRow]`, `warehouse: dict[str, int]` (sku → warehouse_physical_stock)

**Output**: `list[RebalanceRow]`

```python
# Group inventory by sku
# Untuk setiap sku yang ada di warehouse:

shopee_stock = inventory_lookup(sku, "shopee") or 0
tiktok_stock = inventory_lookup(sku, "tiktok") or 0
wh_stock = warehouse[sku]

needs_rebalance = (shopee_stock <= 5 or tiktok_stock <= 5) and wh_stock > 50

if needs_rebalance:
    level = "warning"
    # Recommendation text
    recommendations = []
    if shopee_stock <= 5:
        recommendations.append(f"Replenish Shopee (+{min(100, wh_stock // 2)} unit)")
    if tiktok_stock <= 5:
        recommendations.append(f"Replenish TikTok (+{min(100, wh_stock // 2)} unit)")
else:
    level = "positive"
    recommendations = []

# RebalanceRow shape:
{
    "sku": str,
    "product_name": str,
    "warehouse_stock": int,
    "shopee_stock": int,
    "tiktok_stock": int,
    "level": str,             # "warning" / "positive"
    "recommendations": list[str],
}
```

**Filter**: Hanya tampilkan rows dimana `level == "warning"`. Yang `"positive"` tidak perlu ditampilkan.

**Sort**: `warehouse_stock` descending (paling banyak stok idle di atas).

**Edge case**: SKU ada di warehouse tapi tidak ada di inventory marketplace → tampilkan dengan `shopee_stock = 0` dan `tiktok_stock = 0`.

---

## 5. File Parser (`parser.py`)

Parser mendukung berbagai format file tabular: **CSV** (`.csv`), **Excel** (`.xlsx`, `.xls`), dan **TSV** (`.tsv`).
Format file dideteksi secara otomatis melalui parameter `filename` (ekstensi file) atau inspeksi header/magic bytes file:
- **CSV & TSV**: Mendukung encoding UTF-8, UTF-8-BOM (`utf-8-sig`), dan fallback ke `latin-1`. Delimiter dideteksi secara otomatis (koma `,` untuk CSV, tab `\t` untuk TSV, atau menggunakan `csv.Sniffer`).
- **Excel (`.xlsx`, `.xls`)**: Diproses menggunakan engine pembaca spreadsheet (seperti `openpyxl`). Parser membaca lembar kerja pertama (*active sheet*), mengonversi sel baris pertama menjadi daftar header kolom, dan sel baris berikutnya menjadi baris data tabel persis seperti alur parsing CSV.

### Validation Rules

1. Format file harus valid dan didukung (CSV, TSV, atau Excel `.xlsx`/`.xls`). Jika file biner tidak didukung atau korup, parser menolak file dan melempar error.
2. Header row (baris pertama) harus mengandung semua kolom `Required = yes` dari schema di Section 2.1
3. Kolom matching case-insensitive dan strip whitespace
4. Semua kolom numerik: strip whitespace, bersihkan separator titik ribuan (misal `"129.000"` → `129000`), convert to int. Jika gagal → skip row, log warning.
5. Jika file kosong (hanya header, 0 data rows) → return empty list, bukan error

### Parser Function Signatures

```python
def parse_shopee_orders(file_content: bytes, filename: str = "") -> tuple[list[OrderRow], list[str]]:
    """Returns (parsed_rows, warnings). Mendukung CSV, Excel (.xlsx/.xls), dan TSV."""
    pass

def parse_tiktok_orders(file_content: bytes, filename: str = "") -> tuple[list[OrderRow], list[str]]:
    """Returns (parsed_rows, warnings). Mendukung CSV, Excel (.xlsx/.xls), dan TSV."""
    pass

def parse_shopee_inventory(file_content: bytes, filename: str = "") -> tuple[list[InventoryRow], list[str]]:
    """Returns (parsed_rows, warnings). Mendukung CSV, Excel (.xlsx/.xls), dan TSV."""
    pass

def parse_tiktok_inventory(file_content: bytes, filename: str = "") -> tuple[list[InventoryRow], list[str]]:
    """Returns (parsed_rows, warnings). Mendukung CSV, Excel (.xlsx/.xls), dan TSV."""
    pass

def parse_cogs_csv(file_content: bytes, filename: str = "") -> tuple[list[COGSRow], list[str]]:
    """Returns (parsed_rows, warnings). Mendukung CSV, Excel (.xlsx/.xls), dan TSV."""
    pass
```

Setiap parser return tuple: (list data, list warning strings). Warning contoh: `"Row 15: kolom 'quantity' bukan angka, row dilewati"`.

### Error vs Warning

- **Error** (raise exception, stop): Format file tidak didukung / rusak, atau header column required tidak ditemukan
- **Warning** (skip row, lanjut): Satu row punya data invalid

---

## 6. API Endpoints (`app.py`)

Semua endpoint menggunakan JSON request/response kecuali file upload (multipart/form-data).

### 6.1 `POST /api/analyze`

Main endpoint. Menerima 4 data files (CSV, Excel `.xlsx`/`.xls`, atau TSV) + campaign settings, return full analysis.

**Request**: `multipart/form-data`

| Field | Type | Required |
|---|---|---|
| `shopee_orders` | file (CSV / Excel / TSV) | yes |
| `tiktok_orders` | file (CSV / Excel / TSV) | yes |
| `shopee_inventory` | file (CSV / Excel / TSV) | yes |
| `tiktok_inventory` | file (CSV / Excel / TSV) | yes |
| `campaign_budget` | int (form field) | yes |

**Response**: `200 OK`

```json
{
    "margin_alerts": [ ...MarginAlert ],
    "budget_status": { ...BudgetStatus },
    "run_rate": [ ...RunRateRow ],
    "rebalance": [ ...RebalanceRow ],
    "unmapped_skus": ["SKU-XXX", "SKU-YYY"],
    "warnings": ["Row 15: ...", "Row 22: ..."],
    "summary_text": "RINGKASAN MARKETPLACE MONITOR\n..."
}
```

**Error Responses**:

- `400 Bad Request` (Validasi skema/format/parameter gagal):
```json
{
    "error": "Kolom 'sku_reference_no' tidak ditemukan di file Shopee Orders"
}
```

- `413 Request Entity Too Large` (Total upload melebihi batas 16 MB):
```json
{
    "error": "Ukuran file terlalu besar. Total file yang diunggah tidak boleh melebihi 16 MB."
}
```

- `429 Too Many Requests` (Rate limit terlampaui atau permintaan duplikat sedang berjalan):
```json
{
    "error": "Terlalu banyak permintaan. Silakan tunggu 6 detik sebelum mencoba lagi.",
    "retry_after": 6
}
```
*(Header HTTP menyertakan `Retry-After: 6`)*

### 6.2 `POST /api/cogs/upload`

Upload COGS data file (CSV, Excel `.xlsx`/`.xls`, atau TSV). Bulk insert/replace ke SQLite.

**Request**: `multipart/form-data` — field `cogs_file` (CSV / Excel / TSV)

**Response**: `200 OK`

```json
{
    "inserted": 50,
    "message": "50 SKU berhasil disimpan"
}
```

### 6.3 `GET /api/cogs`

Ambil semua COGS data dari SQLite.

**Response**: `200 OK`

```json
{
    "data": [ ...COGSRow ],
    "count": 50
}
```

### 6.4 `PUT /api/cogs/<sku>`

Update HPP satu SKU.

**Request**: `application/json`

```json
{
    "hpp_per_unit": 70000
}
```

**Response**: `200 OK`

```json
{
    "sku": "SKU-SUNSCREEN-01",
    "hpp_per_unit": 70000,
    "message": "HPP berhasil diupdate"
}
```

**Error**: `404 Not Found` jika SKU tidak ada.

### 6.5 `DELETE /api/cogs/<sku>`

Hapus satu SKU dari COGS.

**Response**: `200 OK`

```json
{
    "message": "SKU-XXX berhasil dihapus"
}
```

### 6.6 `GET /api/sample-data`

Load sample/simulation data untuk demo. Baca file CSV dari folder `data/` dan jalankan analisis menggunakan logic yang sama seperti `POST /api/analyze`.

**Response**: sama seperti `POST /api/analyze` response shape.

Hardcode `campaign_budget = 5000000` untuk sample data.

---

## 7. Summary Text Generator

Tombol "Salin Ringkasan" generate plain text (bukan HTML) yang bisa langsung paste ke WhatsApp.

### Format

```
RINGKASAN MARKETPLACE MONITOR
Campaign: {campaign_name}
Waktu: {current_datetime}
=============================

BUDGET: Rp {total_loss} / Rp {budget} ({pct}% terpakai) — {STATUS}

ALERT JUAL RUGI ({count} order)
- {sku} | {channel} | Rugi Rp {abs(margin)}/unit
- {sku} | {channel} | Rugi Rp {abs(margin)}/unit
...

PREDIKSI HABIS ({count} SKU kritis)
- {sku} | {channel} | Habis ~{stockout_time} ({hours}j lagi)
- {sku} | {channel} | Habis ~{stockout_time} ({hours}j lagi)
...

PERLU REPLENISH ({count} SKU)
- {sku} | Gudang: {wh} | Shopee: {sp} | TikTok: {tt}
...
```

### Alert Card Copy Text

Saat klik satu alert card, copy text per-item:

```
ALERT: {sku} ({product_name}) jual rugi -{margin}/unit di {channel}. Harga jual Rp {actual}, HPP Rp {hpp}. Segera cek voucher.
```

---

## 8. Frontend Behavior (`app.js`)

### 8.1 File Upload

- 4 `<input type="file" accept=".csv, .xlsx, .xls, .tsv">` elements, masing-masing di dalam upload slot
- Saat file dipilih: tampilkan nama file, ubah border ke filled state (lihat design.md 4.3)
- Validasi client-side: periksa ekstensi file (`.csv`, `.xlsx`, `.xls`, `.tsv`). Tampilkan peringatan jika user memilih file di luar format yang didukung. Validasi data dan struktur kolom dilakukan di backend.

### 8.2 Analyze Button

- Disabled sampai semua 4 file terisi
- Saat diklik: kumpulkan 4 files + campaign_budget dari input → `FormData` → `POST /api/analyze`
- **In-Flight Locking & Anti-Double-Click**:
  - Saat tombol diklik, set flag status `isAnalyzing = true`, ubah atribut `disabled = true`, pasang kelas CSS `.is-loading`, ubah teks tombol menjadi `"Memproses..."`, dan tampilkan animasi indikator loading.
  - Setiap klik tambahan atau penekanan tombol Enter berulang saat proses berjalan wajib diabaikan secara total (anti double-click).
  - Menggunakan `AbortController` dengan batas timeout 30 detik untuk membatalkan request jika koneksi internet terputus atau menggantung (sesuai batas toleransi AC 1).
  - State tombol dan flag `isAnalyzing` di-reset kembali hanya di dalam blok `finally` (baik saat request berhasil maupun gagal).
- **State Preservation on Failure**: Jika request gagal karena gangguan jaringan atau error server, file yang sudah dipilih di form dan input budget TIDAK dihapus/direset, sehingga operator tidak perlu memilih ulang file.
- Saat response diterima: render results ke DOM

### 8.3 Tab Switching

- 3 tabs: "Jual Rugi", "Prediksi Habis", "Rebalancing"
- Tab switch pure client-side (show/hide). Tidak ada API call.
- Data sudah ada semua dari satu `/api/analyze` call.

### 8.4 Copy to Clipboard

- Klik alert card → `navigator.clipboard.writeText(alertText)` → tampilkan toast
- Tombol "Salin Ringkasan" → `navigator.clipboard.writeText(summaryText)` → tampilkan toast
- `summary_text` sudah di-generate oleh backend dan ada di response `/api/analyze`

### 8.5 Sample Data Button

- Saat empty state: tombol "Muat Data Sample 10.10"
- Klik → `GET /api/sample-data` → render results (sama seperti habis analyze)
- Sembunyikan upload area, tampilkan banner "Menggunakan data sample"

### 8.6 COGS Management

- Saat pertama kali buka dan belum ada COGS di database: tampilkan upload COGS slot di area terpisah (di atas upload file marketplace, dengan `accept=".csv, .xlsx, .xls, .tsv"`)
- Setelah COGS sudah ada: tampilkan jumlah SKU yang tersimpan + link "Kelola HPP"
- "Kelola HPP" buka inline table dengan kolom: SKU, Nama, HPP, Aksi (Edit/Hapus)
- Edit: inline edit field HPP → save via `PUT /api/cogs/<sku>`
- Upload ulang file COGS (CSV / Excel): replace semua data

### 8.7 UI-First Development & Interactive Mock Strategy

Untuk memungkinkan pengembangan frontend secara utuh sebelum integrasi backend, `static/app.js` dirancang dengan arsitektur **UI-First**:
- **Mock State / Fixtures**: Menyediakan mock data yang strukturnya identik dengan kontrak `/api/analyze` (Section 6.1) dan `/api/cogs` (Section 6.3).
- **Interactive UI Testing**: Developer dapat langsung menguji dan memverifikasi visualisasi dashboard, perpindahan 3 tab, interaksi copy card & summary, toast notification 3 detik, budget meter, dan modal/tabel COGS di browser tanpa menunggu backend selesai.
- **State Toggling**: Menyediakan helper internal untuk mensimulasikan semua UX states (`Empty`, `Loading`, `Results`, `Error`) secara instan di UI.
- **Clean API Decoupling**: Saat backend siap di Phase 4, developer cukup mengganti mock data provider dengan fungsi `fetch()` nyata ke endpoint Flask tanpa mengubah struktur DOM atau CSS.

### 8.8 Network Resilience & Client Guardrails

- **Client-Side File Size Pre-check**: Sebelum request dikirim via network, client memeriksa ukuran masing-masing file (`file.size`). Jika ada file > 10 MB atau total 4 file > 16 MB, batalkan pengiriman seketika dan tampilkan alert banner di UI: `"Ukuran file terlalu besar (maksimal 10 MB per file, 16 MB total)."`.
- **Offline & Disconnection Handling**: Mendengarkan event `window.addEventListener('offline')` dan menangani error `fetch()` (network drop / failed to fetch). Tampilkan pesan informatif yang ramah operator: `"Koneksi internet bermasalah. Periksa jaringan Anda dan coba lagi."`.
- **429 Rate Limit Feedback**: Jika menerima response `429 Too Many Requests`, baca nilai `retry_after`, disable tombol submit selama durasi tersebut, dan tampilkan countdown timer di toast/banner: `"Terlalu banyak permintaan. Silakan tunggu X detik..."`.
- **State Preservation on Re-enable**: Saat request dibatalkan karena timeout atau error jaringan, form file input dan nilai input budget tetap terjaga utuh. Operator tidak perlu memilih file dari awal saat ingin mencoba submit kembali.

---

## 9. Edge Cases & System Guardrails

### 9.1 Data & Calculation Edge Cases

| Case | Handling |
|---|---|
| CSV encoding bukan UTF-8 | Coba decode `utf-8-sig` (BOM), lalu `latin-1` sebagai fallback |
| Upload file Excel (.xlsx / .xls) atau TSV (.tsv) | Didukung penuh. Parser membaca sheet pertama (*active sheet*) pada file Excel atau mendeteksi delimiter tab pada TSV, lalu memetakan kolom ke schema internal |
| File Excel memiliki multiple sheets | Parser otomatis membaca lembar kerja pertama (*active/first sheet*) secara default |
| Kolom required tidak ada di header | Return `400` dengan pesan spesifik kolom mana yang missing |
| Angka punya separator titik (e.g. "129.000") | Strip titik sebelum parse int: `value.replace(".", "")` |
| SKU ada di orders tapi tidak ada di COGS | Skip dari margin analysis, tambahkan ke `unmapped_skus` list |
| SKU ada di COGS tapi tidak ada di orders | Tidak masalah, diabaikan |
| Velocity = 0 (tidak ada order untuk SKU tertentu) | `hours_until_stockout = infinity`, tampilkan "∞" di UI |
| Channel stock = 0 | `hours_until_stockout = 0`, level = "negative" |
| Campaign budget = 0 | `pct_used = 0`, `meter_level = "safe"` |
| Upload file kosong (hanya header) | Return empty results, tidak error |
| Duplicate order_id di file order | Proses semua, tidak deduplicate (marketplace bisa punya multiple lines per order untuk multi-item) |
| File bukan format tabular yang didukung (e.g. .pdf, .docx, file binary rusak) | Client-side: filter via `accept=".csv, .xlsx, .xls, .tsv"`. Server-side: return `400` jika format tidak didukung atau parse gagal |

### 9.2 System Guardrails & Operational Resilience

Dalam situasi midnight mega-sale (10.10 rush), operator beroperasi di bawah tekanan tinggi dengan kondisi koneksi internet yang fluktuatif atau lambat. Sistem menerapkan guardrails ketat pada layer antarmuka dan backend:

#### 9.2.1 Multiple Submissions & Network Latency Protection (Anti Double-Click)
- **User Problem**: Saat mengunggah 4 file besar di koneksi 4G/Wi-Fi yang lambat, request butuh 3-5 detik. Operator yang cemas cenderung mengklik tombol `[ Analisis Sekarang ]` berkali-kali secara agresif. Tanpa guardrail, ini memicu multiple HTTP uploads dan membebani server dengan eksekusi parsing paralel yang identik.
- **Client-Side Guard (In-Flight Lock)**:
  - Seketika tombol diklik, sistem menetapkan flag global `isAnalyzing = true`, memberi atribut `disabled = true` pada tombol submit, menambahkan kelas CSS `.is-loading`, dan mengganti teks tombol menjadi `"Memproses..."`.
  - Event click lanjutan atau penekanan tombol `Enter` berulang saat request sedang aktif diabaikan (*debounced/locked*).
  - Timeout diatur ke 30 detik menggunakan JavaScript `AbortController`. Jika server tidak merespons dalam 30 detik, request di-abort otomatis dan muncul pesan error: `"Waktu permintaan habis (timeout 30 detik). Koneksi lambat, silakan coba lagi."`.
  - Tombol di-enable kembali secara aman hanya di blok `finally` (setelah response tuntas diterima atau gagal).
  - **Form State Preservation**: Jika request dibatalkan karena timeout atau network drop, pilihan file pada 4 slot dropzone dan nilai budget tetap dipertahankan. Operator tidak perlu memilih ulang file dari awal.
- **Server-Side Guard (Concurrent In-Flight Mutex)**:
  - Dikelola di `guardrails.py` menggunakan active request lock berbasis IP address pemohon (`request.remote_addr`).
  - Jika request `POST /api/analyze` dari IP yang sama masih dalam status diproses, request baru yang masuk seketika ditolak dengan status HTTP `429 Too Many Requests` (atau `409 Conflict`) dengan body:
    ```json
    {
      "error": "Permintaan analisis sebelumnya sedang diproses. Harap tunggu hingga selesai."
    }
    ```
  - Mencegah CPU spike dan pemborosan I/O akibat parsing paralel file yang sama.

#### 9.2.2 In-Memory API Rate Limiting (Throttling)
- **Arsitektur**: Mengingat batasan arsitektur (zero database server / no Redis), rate limiting diimplementasikan secara murni in-memory menggunakan standard library Python (`collections`, `time`, `threading.Lock`) di dalam modul `guardrails.py`.
- **Mekanisme**: Menggunakan algoritma *Sliding Window Counter* per IP address (`request.remote_addr`) untuk mencegah abuse, automated bot spamming, atau runaway client loop.
- **Ambang Batas (Tiered Limits)**:
  | Endpoint | Limit | Window | Alasan |
  |---|---|---|---|
  | `POST /api/analyze` | 10 requests | 1 menit (60 detik) | Operasi berat (I/O 4 file, multi-format parse, engine join) |
  | `POST /api/cogs/upload` | 10 requests | 1 menit (60 detik) | Operasi write bulk SQLite |
  | `GET /api/sample-data` | 20 requests | 1 menit (60 detik) | Fast disk-read & engine compute |
  | `PUT /api/cogs/<sku>` & `DELETE /api/cogs/<sku>` | 30 requests | 1 menit (60 detik) | Mutasi baris tunggal |
  | `GET /api/cogs` | 60 requests | 1 menit (60 detik) | Fast read SQLite |
- **Spesifikasi Response HTTP 429**:
  - Status Code: `429 Too Many Requests`
  - Header HTTP: `Retry-After: <seconds>` (durasi detik tersisa sebelum kuota pulih)
  - Body JSON:
    ```json
    {
      "error": "Terlalu banyak permintaan. Silakan tunggu {retry_after} detik sebelum mencoba lagi.",
      "retry_after": 6
    }
    ```
  - **Client UI Feedback**: Antarmuka mendeteksi response 429, membaca `retry_after`, dan mengunci tombol dengan indikator hitung mundur (countdown toast/banner).

#### 9.2.3 Payload & Memory Guards (`MAX_CONTENT_LENGTH`)
- **Server Guard**: Flask dikonfigurasi dengan `app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024` (16 MB).
- Jika total payload multipart melebihi 16 MB, Flask otomatis menolak request dengan status HTTP `413 Request Entity Too Large`.
- Error handler khusus di `app.py` merender JSON ramah operator:
  ```json
  {
    "error": "Ukuran file terlalu besar. Total file yang diunggah tidak boleh melebihi 16 MB."
  }
  ```
- **Client Pre-Flight Guard**: Sebelum transmisi dimulai, `static/app.js` memeriksa ukuran setiap file (`file.size`). Jika ada file > 10 MB atau total 4 file > 16 MB, proses submit langsung dibatalkan sebelum menyentuh jaringan dengan pesan peringatan di UI.

#### 9.2.4 Network Disconnection & Offline Handling
- Client memasang listener `window.addEventListener('offline')` untuk menampilkan alert banner status offline jika sambungan internet operator terputus di tengah campaign.
- Blok penanganan error `fetch()` membedakan antara network error (misal `TypeError: Failed to fetch` akibat putus kabel/Wi-Fi hilang) dengan HTTP status error:
  - Network failure: Toast feedback `"Koneksi internet terputus saat menghubungi server. Periksa jaringan Anda dan coba lagi."`.
  - State form di-preserve sehingga operator cukup menekan kembali tombol saat jaringan pulih.

#### 9.2.5 Input Bounds & Row Count Limits
- **Campaign Budget Bounds**: Parameter `campaign_budget` divalidasi sebagai integer non-negatif (`0 <= budget <= 1.000.000.000.000`). Nilai negatif atau string tidak valid mengembalikan HTTP `400 Bad Request`.
- **Max Row Limit**: Parser tabular (`parser.py`) membatasi maksimal 50.000 baris per file untuk mencegah thread worker terkunci (*denial of service*) saat membaca file abnormal. Melebihi batas ini mengembalikan HTTP `400 Bad Request`.

---

## 10. Implementation Phases (UI-First Workflow)

Pendekatan implementasi menggunakan strategi **UI-First**: Membangun fondasi server minimal dan styling, mengimplementasikan seluruh antarmuka pengguna (UI/UX) dan interaksi visual secara lengkap dengan mock data, kemudian membangun backend engines dan mengintegrasikannya.

> **Penting untuk Sesi AI & Antigravity**: Sebelum memulai pengerjaan fase apa pun, wajib membaca `learnings.md` untuk memahami status terkini dan catatan dari sesi sebelumnya. Setelah menyelesaikan fase atau sebelum sesi berakhir, selalu perbarui `learnings.md` dengan progress terbaru, keputusan teknis, gotchas yang ditemukan, dan next steps sesuai *AI Session Continuity Protocol*.

```
[Phase 1: Foundation Setup]
         ↓
[Phase 2: Complete UI & Client-Side Prototype (UI-First)]
         ↓
[Phase 3: Backend Core & Calculation Engine]
         ↓
[Phase 4: API Endpoints & Backend-Frontend Integration]
         ↓
[Phase 5: System Guardrails, Resilience & Request Throttling]
         ↓
[Phase 6: End-to-End Acceptance Verification & Polish]
```

### Phase 1 — Project Foundation & Dev Server Setup (Foundational Step)

Langkah fondasi minimal agar developer dapat menjalankan server lokal dan langsung mem-preview UI secara hot/live di browser.

Deliverables:
- Scaffolding struktur direktori (`templates/`, `static/`, `instance/`, `data/`).
- Minimal `app.py`: Flask instance dasar dengan route `GET /` yang me-render `templates/index.html` dan melayani file statis (`static/style.css`, `static/app.js`).
- `templates/index.html`: Kerangka HTML dasar yang memuat Google Fonts CDN (`Inter`, `JetBrains Mono`) dan me-link `style.css` serta `app.js`.
- `static/style.css`: Inisialisasi **seluruh design tokens** dari `design.md` (Colors: `--gray-50` s/d `--gray-900`, Accent `--blue-500`, Status `--status-*`, Meter `--meter-*`; Typography: `--font-sans`, `--font-mono`, scale `--text-*`; Spacing & Radius; CSS reset & base layout).

Bisa ditest:
- Jalankan `python app.py` → akses `http://localhost:5000` berhasil (status `200 OK`).
- `test_frontend_design_tokens_css` di `tests/test_frontend.py` lolos/PASS.

### Phase 2 — Complete UI & Interactive Frontend Prototype (UI-First)

Mengimplementasikan seluruh visual layout, komponen dashboard, dan interaksi client-side sesuai `PRODUCT_SPEC.md` dan `design.md` menggunakan data mock sebelum menulis logic backend.

Deliverables:
- `templates/index.html`: Struktur lengkap semua komponen visual (aturan ketat: **TIDAK ADA EMOJI**):
  - **Header Bar**: Title ("SIRCLO Marketplace Monitor"), status badge, subjudul campaign.
  - **COGS / HPP Section**: Slot upload file COGS, SKU counter badge, dan tabel inline collapsible "Kelola HPP" dengan baris sample, field input HPP, tombol Aksi (Edit/Hapus).
  - **Upload Area (4 Dropzones)**: 4 file input slots (`shopee_orders`, `tiktok_orders`, `shopee_inventory`, `tiktok_inventory`) dengan atribut `accept=".csv, .xlsx, .xls, .tsv"` dan status visual drag-over/filled, input campaign budget berawalan Rupiah (`Rp`), tombol `[ 📊 Analisis Sekarang ]` dan `[ Muat Data Sample 10.10 ]`.
  - **Budget Meter**: Display total kerugian angka besar (`--text-num-lg`), batas budget, sisa budget, progress bar dengan level warna dinamis (`--meter-safe`, `--meter-caution`, `--meter-over`).
  - **Tabbed Results Section**: 3 tab ("Jual Rugi", "Prediksi Habis", "Rebalancing") lengkap dengan badge counter jumlah item.
  - **Tab 1 — Jual Rugi**: Grid alert card dengan badge warna status (merah/kuning/hijau), rincian harga beli vs HPP, nominal kerugian per unit, dan target klik untuk copy alert.
  - **Tab 2 — Prediksi Habis**: Tabel data dengan kolom SKU, channel, total terjual, run rate/jam, stok marketplace, prediksi jam habis, badge status urgensi, serta simbol "∞" untuk SKU tanpa penjualan.
  - **Tab 3 — Rebalancing**: Kartu rebalancing untuk SKU dengan stok channel kritis (≤ 5) dan stok gudang berlebih (> 50), disertai rekomendasi penambahan stok.
  - **Summary Action & Drawer**: Tombol "Salin Ringkasan" dan preview ringkasan teks WhatsApp.
  - **Toast Element**: Container toast fixed (`#toast`) untuk feedback copy teks ("Pesan aksi disalin", "Ringkasan disalin ke clipboard").
  - **State Containers**: Container untuk `Empty State`, `Loading State` (indikator proses), `Results State`, dan banner `Error State`.
- `static/style.css`:
  - Styling lengkap semua komponen di atas sesuai token `design.md` (clean, muted Stripe/Vercel dashboard aesthetic).
  - Responsiveness: Penyesuaian layout pada breakpoint tablet/mobile (768px).
  - Format tipografi angka monospace (`--font-mono`) untuk nilai Rupiah dan metrik numerik.
- `static/app.js`:
  - Logika perpindahan tab murni di client-side (show/hide panel).
  - Interaksi drag/drop & pemilihan file (update visual upload slot ke status terisi; filter ekstensi `.csv`, `.xlsx`, `.xls`, `.tsv`).
  - Mock Data Controller: Inject data mock (mengikuti schema Section 6.1) untuk menampilkan state hasil analisis secara instan.
  - Event listener klik pada alert card → copy teks aksi per-item ke clipboard + trigger toast (hilang dalam 3 detik).
  - Event listener tombol "Salin Ringkasan" → copy teks ringkasan lengkap ke clipboard + trigger toast (3 detik).
  - Tombol toggle untuk demonstrasi visual: Empty State, Loading State, Results State, Error State.

Bisa ditest:
- Seluruh unit test di `tests/test_frontend.py` lolos 100% (`test_frontend_upload_slots_present`, `test_frontend_tabs_present`, `test_frontend_budget_meter_elements`, `test_frontend_design_tokens_css`, `test_frontend_no_emoji_rule`, `test_frontend_toast_element_present`, `test_frontend_copy_summary_button_present`, `test_frontend_cogs_section_present`).
- Pengguna dapat membuka browser, melihat seluruh UI dengan sempurna, berpindah antar tab, mengklik copy card, melihat toast muncul dan hilang, serta mengecek responsivitas layout tanpa ketergantungan backend.

### Phase 3 — Backend Core (Database, Parsers, Calculation Engine & Summary)

Membangun seluruh fondasi data, parser multi-format (CSV, Excel `.xlsx`/`.xls`, TSV), dan engine kalkulasi bisnis secara murni di sisi backend (unit-tested independen).

Deliverables:
- `db.py`:
  - Inisialisasi SQLite (`instance/cogs.db`) & schema tabel `cogs` (`init_db`).
  - Fungsi CRUD: `bulk_insert_cogs()`, `get_all_cogs_dict()`, `get_all_cogs_list()`, `update_cogs_hpp()`, `delete_cogs_sku()`.
- `parser.py`:
  - Implementasi parser serbaguna: `parse_shopee_orders()`, `parse_tiktok_orders()`, `parse_shopee_inventory()`, `parse_tiktok_inventory()`, `parse_cogs_csv()`.
  - Dukungan format: CSV, Excel (`.xlsx`, `.xls`), dan TSV (`.tsv`).
  - Penanganan sheet pertama workbook Excel secara otomatis.
  - Penanganan encoding fallback (UTF-8, UTF-8-BOM / `utf-8-sig`, `latin-1`) untuk file teks.
  - Penanganan angka dengan separator titik Indonesia (e.g. `"129.000"` → `129000`).
  - Validasi header wajib (error jika missing) dan validasi baris (skip & catat warning jika invalid numeric).
- `engine.py`:
  - `calculate_margins()`: perhitungan margin, klasifikasi level (`negative`, `warning`, `positive`), penanganan SKU tak terdaftar (`unmapped_skus`).
  - `calculate_budget()`: total kerugian, persentase budget, klasifikasi status meter (`safe`, `caution`, `over`).
  - `calculate_run_rate()`: hitung velocity penjualan/jam, prediksi jam habis, penanganan velocity = 0 (`hours_until_stockout = inf`, waktu habis = `None`).
  - `calculate_rebalance()`: deteksi stok channel ≤ 5 dengan stok gudang > 50, kalkulasi rekomendasi unit replenish.
- `summary.py`:
  - `generate_summary_text()`: plain text generator untuk ringkasan laporan WhatsApp sesuai format Section 7.
  - `generate_alert_copy_text()`: generator teks salin untuk individual alert card.

Bisa ditest:
- `test_db.py` lolos 100% (tabel dibuat, CRUD berjalan, upsert berhasil).
- `test_parser.py` lolos 100% (semua file tabular ter-parse, validasi kolom error, row warning tercatat).
- `test_engine.py` lolos 100% (kalkulasi margin, budget meter, run rate, rebalance akurat).
- `test_summary.py` lolos 100% (format WhatsApp rapi, format Rupiah tepat).

### Phase 4 — API Endpoints & Backend-Frontend Integration

Menghubungkan frontend yang sudah jadi di Phase 2 dengan backend core di Phase 3 melalui REST API endpoints.

Deliverables:
- Endpoints di `app.py`:
  - `POST /api/analyze`: Menerima 4 file data (CSV / Excel / TSV) + `campaign_budget` via multipart form-data, menjalankan parsing, memanggil engine & summary generator, mengembalikan JSON unified analysis.
  - `GET /api/sample-data`: Membaca dataset dari folder `data/`, mengeksekusi pipeline analisis yang sama dengan default budget Rp 5.000.000.
  - `POST /api/cogs/upload`: Upload file HPP (CSV / Excel / TSV) bulk ke SQLite.
  - `GET /api/cogs`: Ambil seluruh daftar SKU COGS.
  - `PUT /api/cogs/<sku>` & `DELETE /api/cogs/<sku>`: Update HPP dan hapus SKU.
- Integrasi Frontend (`static/app.js`):
  - Mengganti mock data provider dengan pemanggilan API nyata (`fetch()`).
  - Form submit upload 4 file (CSV / Excel / TSV) + campaign budget mengirim `FormData` ke `POST /api/analyze`.
  - Tombol "Muat Data Sample 10.10" memanggil `GET /api/sample-data` dan merender data nyata dari backend.
  - Upload HPP dan aksi tabel "Kelola HPP" terhubung ke `/api/cogs/*`.
  - Mengikat penanganan error (HTTP 400) ke banner pesan error di UI.
  - Mengikat payload `summary_text` dan teks alert dari response backend ke fungsi clipboard.

Bisa ditest:
- `test_api.py` lolos 100% (semua endpoint mengembalikan format response dan status code yang sesuai).
- `test_integration.py` lolos 100% (aliran data dari file upload hingga output response teruji utuh).
- Upload file asli (CSV atau Excel) di browser menghasilkan visual dashboard yang akurat dengan data sebenarnya.

### Phase 5 — System Guardrails, Resilience & Request Throttling

Membangun lapisan ketahanan sistem (*hardening & resilience guardrails*) baik pada antarmuka frontend maupun backend untuk menangani skenario koneksi internet buruk, double submit / spam klik tombol oleh operator, pembatasan laju request (*rate limiting*), proteksi memori payload, serta pemulihan dari kegagalan jaringan.

Deliverables:
- `guardrails.py`:
  - Modul in-memory thread-safe rate limiter (algoritma Sliding Window Counter) menggunakan standard library Python (`collections`, `time`, `threading.Lock`) tanpa dependensi database eksternal.
  - Mekanisme *in-flight concurrent request lock* berbasis IP address pemohon (`request.remote_addr`) untuk mendeteksi dan menolak eksekusi ganda pada endpoint komputasi berat (`POST /api/analyze`).
  - Helper / decorator `@rate_limit(limit, window)` dan context manager / lock checker untuk endpoint Flask.
- Server-Side Guards (`app.py`):
  - Integrasi rate limiter pada semua API endpoints (`POST /api/analyze`, `POST /api/cogs/upload`, `GET /api/sample-data`, `/api/cogs/*`) sesuai ambang batas di Section 9.2.2.
  - Handler response HTTP `429 Too Many Requests` terstruktur menyertakan header `Retry-After: <seconds>` dan body JSON `{"error": "...", "retry_after": ...}`.
  - Penolakan request identik serentak (concurrent in-flight duplicate) dengan status HTTP 429 atau 409 (`{"error": "Permintaan analisis sebelumnya sedang diproses. Harap tunggu hingga selesai."}`).
  - Konfigurasi `app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024` (16 MB) dan custom error handler HTTP `413 Request Entity Too Large` dengan respon JSON.
  - Validasi batas nilai numerik (*bounds check*) untuk parameter `campaign_budget` (integer non-negatif `0 <= budget <= 1.000.000.000.000`), return HTTP 400 jika invalid.
  - Batas maksimal pembacaan 50.000 baris per file tabular pada `parser.py` (return HTTP 400 jika melampaui batas).
- Client-Side Guards (`static/app.js`):
  - **In-flight lock & debouncing**: Disable tombol submit segera saat diklik (`btn.disabled = true`), pasang kelas CSS `.is-loading`, ubah teks tombol menjadi `"Memproses..."`, pasang flag `isAnalyzing = true`. Abaikan seluruh klik dan tombol Enter berikutnya.
  - **Timeout control**: Integrasi `AbortController` dengan batas waktu 30 detik. Batalkan request jika server tidak merespons dalam 30 detik dan tampilkan pesan error timeout.
  - **Re-enable & state preservation**: Tombol submit selalu di-enable kembali di blok `finally`. File input dan input budget tetap dipertahankan (tidak di-reset) saat request gagal agar operator tidak perlu upload ulang.
  - **Pre-flight file size check**: Validasi ukuran file di browser sebelum dikirim (maksimal 10 MB per file, 16 MB total).
  - **Offline & network failure recovery**: Deteksi status `navigator.onLine` / event `offline`, tangkap error koneksi (`TypeError: Failed to fetch`), tampilkan toast/banner error jaringan yang ramah operator.
  - **Rate limit countdown**: Tangani response HTTP 429 dengan membaca header/body `retry_after` dan menampilkan hitung mundur waktu tunggu di antarmuka sebelum tombol aktif kembali.
- Unit & Guardrail Tests (`tests/test_guardrails.py`):
  - Uji in-memory rate limiter: kuota request terpenuhi, penolakan HTTP 429 pada batas limit + 1, reset kuota setelah window 60 detik.
  - Uji concurrent request lock: request kedua yang masuk saat request pertama masih berjalan di `/api/analyze` ditolak seketika.
  - Uji proteksi ukuran file: payload melebihi 16 MB mengembalikan HTTP 413 JSON.
  - Uji validasi input budget: nilai negatif atau bukan angka mengembalikan HTTP 400.
  - Uji client-side behavior via automated DOM/mock checks.

Bisa ditest:
- Seluruh unit test di `tests/test_guardrails.py` lolos 100%.
- Mengirim 11 request beruntun ke `/api/analyze` menghasilkan 10 respon sukses dan 1 respon HTTP 429 dengan header `Retry-After`.
- Mengirim 2 request serentak ke `/api/analyze` dari IP yang sama ditolak oleh concurrent lock.
- Mengunggah payload tiruan > 16 MB menghasilkan respon HTTP 413 dengan pesan JSON.
- Pengujian di browser: klik tombol berkali-kali secara cepat saat koneksi disimulasikan lambat (slow 3G di devtools) hanya menghasilkan 1 HTTP request, tombol tetap berstatus disabled/loading hingga proses tuntas.

### Phase 6 — End-to-End Acceptance Verification & Polish

Tahap final pengujian menyeluruh terhadap seluruh kriteria penerimaan produk, keandalan guardrails sistem, edge cases, dan pemolesan UX.

Deliverables:
- Eksekusi Acceptance Tests (`tests/test_acceptance.py`):
  - Memverifikasi 11 Acceptance Criteria dari `PRODUCT_SPEC.md` secara otomatis.
- Audit Performa & Ketahanan Guardrails:
  - Memastikan waktu analisis dari klik tombol hingga render di browser < 2 detik (jauh di bawah batas toleransi 30 detik AC 1).
  - Memastikan guardrails (rate limit, anti double-click, timeout abort) tidak mengganggu alur operasional normal.
- Pengujian Edge Cases:
  - Upload file Excel (.xlsx / .xls), CSV dengan encoding aneh / BOM, file kosong, format ribuan bertitik.
  - Skenario SKU tanpa penjualan (menampilkan "∞"), SKU tidak ada di COGS (warning banner).
  - Campaign budget 0 atau kerugian melampaui 100% budget.
  - Skenario koneksi lambat dan simulasi offline.
- Polish Visual & Aksesibilitas:
  - Verifikasi tampilan pada resolusi mobile/desktop.
  - Memastikan seluruh aturan `design.md` terpenuhi (bebas emoji, font tokens sesuai, warna status tepat).

Bisa ditest:
- Seluruh suite unit test, guardrail test, & acceptance test lolos hijau (`python -m unittest discover tests`).
- Semua 11 Acceptance Criteria di `PRODUCT_SPEC.md` terpenuhi sepenuhnya.

---

## 11. Sample Data Reference

Gunakan file CSV yang sudah ada di folder `data/`:

| File | Records | Berisi |
|---|---|---|
| `data/shopee_orders.csv` | 50 orders | 9 orders jual di bawah HPP |
| `data/tiktok_orders.csv` | 50 orders | 8 orders jual di bawah HPP |
| `data/shopee_inventory.csv` | 50 SKUs | 6 hero SKUs dengan stock 0 |
| `data/tiktok_inventory.csv` | 50 SKUs | 2 SKUs dengan stock 0 |
| `data/internal_cogs_hpp.csv` | 50 SKUs | HPP reference |
| `data/master_warehouse_inventory_cogs.csv` | 50 SKUs | Warehouse stock + allocation |

Data ini dipakai oleh:
1. `GET /api/sample-data` — load dan analyze otomatis
2. Manual testing — operator upload file-file ini untuk test

---

## 12. Dependencies

### Python packages (install via pip)

```
flask
openpyxl
```

- `flask` untuk lightweight web backend framework
- `openpyxl` untuk membaca dan memproses spreadsheet Excel (`.xlsx`)
- Standard library Python (`csv`, `sqlite3`, `json`, `datetime`, `io`) untuk CSV/TSV parsing, database, dan utility.

### Frontend (CDN, no install)

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
```

Tidak ada library JS. Vanilla JavaScript saja.

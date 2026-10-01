# 🧠 Learnings & Architectural Notes — SIRCLO Marketplace Monitor

Dokumen ini mencatat pembelajaran (*learnings*), keputusan arsitektural (*architectural decisions*), konvensi kode, dan batasan desain penting yang ditemukan selama perancangan dan pengembangan **SIRCLO Marketplace Monitor**.

Dokumen ini berfungsi sebagai pedoman berkelanjutan bagi developer dan AI agent agar konsistensi teknis, estetika desain, serta kebutuhan domain bisnis tetap terjaga.

---

## 1. Domain & Kebutuhan Pengguna (User Context)

### 1.1 Realita Ekspor Marketplace (Shopee & TikTok Shop)
- **Format File Ekspor Fleksibel**: Seller Center tidak selalu mengekspor data dalam bentuk CSV murni; operator kerap mengunduh laporan dalam format **Excel (`.xlsx`, `.xls`)** atau format delimitasi lain seperti **TSV**.
- **User Pain Point**: Memaksa operator mengonversi file Excel ke CSV secara manual sebelum diunggah memperlambat alur kerja midnight sale (10.10 mega-sale) dan meningkatkan risiko kesalahan operator.
- **Keputusan**: Seluruh slot upload (`shopee_orders`, `tiktok_orders`, `shopee_inventory`, `tiktok_inventory`, dan `cogs_file`) wajib menerima **CSV, Excel (`.xlsx`, `.xls`), dan TSV**.

### 1.2 Format Numerik & Lokalisasi Indonesia
- Angka finansial dan stok dari marketplace sering kali menggunakan format ribuan dengan titik (contoh: `"129.000"`).
- Jika langsung di-casting via `int()`, Python akan melempar `ValueError`.
- Parser wajib membersihkan titik ribuan dan whitespace sebelum konversi numerik: `int(str(val).replace(".", "").strip())`.

### 1.3 Strategi Otomasi: Analisis Instan vs. Integrasi API Marketplace (The 80/20 Rule)
- **Bottleneck Sebenarnya**: Waktu operator terbuang pada proses analisis, VLOOKUP, dan formulasi manual di Google Sheets (~40 menit per siklus), bukan pada proses download/drop file dari Seller Center (~2 menit per siklus).
- **Keputusan Otomasi**: **Tidak perlu mengotomasi koneksi API langsung ke Shopee/TikTok Shop atau sinkronisasi ERP pada tahap ini**.
  - Mengotomasi analisis instan via upload file sudah memangkas waktu siklus dari 42 menit ke 2 menit (**efisiensi 95% / percepatan 21x**).
  - Integrasi API marketplace (Shopee Open Platform / TikTok Shop Partner API) memerlukan verifikasi akun developer bisnis, persetujuan aplikasi mitra (berminggu-minggu), manajemen token OAuth2/HMAC-SHA256, serta rawan *throttling* / *rate-limit* pada saat lonjakan trafik *midnight mega-sale* (10.10).
  - ROI integrasi API sangat rendah dibandingkan risiko dan beban pemeliharaannya. Alur drop file CSV/Excel manual tetap menjadi solusi tercepat, paling andal, dan nol biaya integrasi.

### 1.4 Alur Kerja Drop Per Jam & Akumulasi Data (Hourly Drops)
- Operator mengunduh dan mengunggah data baru setiap jam selama periode kampanye.
- **Akumulasi Order (Cumulative Loss & Run-Rate)**:
  - File order per jam dapat di-append ke penyimpanan lokal/SQLite dengan strategi deduplikasi `order_id` (`INSERT OR IGNORE` atau upsert).
  - Hal ini memungkinkan penghitungan *run-rate* kumulatif yang semakin akurat seiring berjalannya kampanye dan pelacakan anggaran *budget safe meter* secara agregat tanpa mengharuskan operator menggabungkan file-file jam sebelumnya secara manual.
- **Snapshot Stok (Inventory Balance)**:
  - Berbeda dengan order yang bertambah (*append-only*), data stok marketplace dan gudang adalah representasi *snapshot* kondisi terkini saat file diunduh, sehingga data stok diperbarui (*replace/upsert*) ke stok terbaru.

---

## 2. Arsitektur File Ingestion & Parsing (`parser.py`)

### 2.1 Multi-Format Reader Pattern
- Untuk mendukung file CSV, Excel, dan TSV tanpa menduplikasi logika validasi skema:
  1. **Deteksi Format**: Deteksi ekstensi file melalui nama file atau inspeksi magic bytes/header file.
  2. **Abstraksi Baris Data**:
     - **CSV / TSV**: Dibaca menggunakan modul `csv` bawaan Python. Deteksi delimiter koma `,` atau tab `\t`. Dukung decoding UTF-8, UTF-8-BOM (`utf-8-sig`), dan fallback ke `latin-1`.
     - **Excel (`.xlsx`)**: Dibaca menggunakan library `openpyxl`. Ambil lembar kerja pertama (*active sheet*), baris 1 sebagai header kolom, dan baris-baris berikutnya sebagai data baris (dikonversi ke format string yang bersih).
  3. **Mapping Skema Bersama**: Setelah baris dan header diekstrak, logika validasi kolom wajib (*Required*), case-insensitivity, dan transformasi ke `OrderRow` / `InventoryRow` / `COGSRow` berjalan identik.

### 2.2 Error vs Warning
- **Error (HTTP 400 / Exception)**:
  - Format file tidak didukung (misal `.pdf`, `.docx`, atau file biner rusak dengan null bytes `\x00`).
  - Kolom wajib (*Required*) tidak ditemukan di header file.
  - Jumlah baris melampaui batas aman `MAX_ROW_LIMIT = 50000` baris.
- **Warning (Skip Row & Catat Log)**:
  - Baris dengan nilai numerik korup (misal teks pada kolom quantity/harga). Baris dilewati dan dicatat ke daftar `warnings` tanpa membatalkan proses baris lainnya.

### 2.3 Sanitasi Numerik Multi-Tipe (`clean_int`)
- Library `openpyxl` sering mengembalikan nilai numerik sel sebagai tipe data Python `int` atau `float` (contoh: `129000.0`), sementara pembaca CSV mengembalikan `str` berformat ribuan lokal Indonesia (contoh: `"129.000"` atau `"129,000"`).
- Helper `clean_int()` menangani ketiga variasi secara terpadu:
  1. Jika tipe `int`, langsung kembalikan nilai integer.
  2. Jika tipe `float`, bulatkan dengan `int(round(val))`.
  3. Jika string, bersihkan titik ribuan dan koma, kemudian lakukan parsing `int(cleaned)`.
  4. Jika string kosong atau `None`, lemparkan `ValueError` untuk ditangkap sebagai baris warning.

### 2.4 Prioritas Pelaporan Header Kolom Wajib
- Saat file CSV diunggah tanpa header yang valid (atau file sembarang), sistem perlu memberikan pesan error yang paling relevan.
- Kolom pengenal produk utama (`sku_reference_no` pada Shopee dan `seller_sku` pada TikTok) diletakkan pada urutan prioritas pertama dalam daftar pengecekan kolom wajib (`req_specs`). Hal ini menjamin bahwa saat baris header salah total, sistem langsung menginformasikan ketiadaan kolom SKU kunci kepada operator.

### 2.5 Ketahanan Header BOM Ganda & Stray Unicode Characters
- Beberapa tool ekspor atau editor spreadsheet menyisipkan karakter BOM Unicode ganda (`\ufeff\ufeff`) atau meninggalkan karakter tak kasat mata di header kolom pertama.
- Meskipun decoding `utf-8-sig` menghilangkan 1 BOM pertama di level byte, karakter BOM kedua tetap tersisa di string kolom pertama (`\ufefforder_id`).
- Melakukan pembersihan eksplisit `h.strip().lstrip('\ufeff')` pada seluruh nama kolom header menjamin pencocokan nama kolom skema (`order_id`, `sku_reference_no`, `seller_sku`) tetap 100% akurat tanpa false failure.

### 2.6 Penutupan File Descriptor & Resource Management (openpyxl & Flask Multipart)
- Ketika membaca spreadsheet Excel dengan mode `read_only=True` via `openpyxl`, objek workbook menahan file handle temporer pada berkas ZipFile.
- Workbook wajib selalu ditutup secara eksplisit via `wb.close()` dalam blok `finally`.
- Pada sisi server Flask, berkas upload multipart yang ditangani oleh `FileStorage` perlu ditutup via hook `@app.after_request` untuk memastikan seluruh temp file buffer dibebaskan secara bersih setelah siklus respons selesai.

---

## 3. Desain Antarmuka & UX (`design.md`)

### 3.1 Aturan Mutlak: Dilarang Menggunakan Emoji (No-Emoji Policy)
- **Aturan Ketat**: Dilarang keras menggunakan karakter emoji Unicode (misal 📊, 🔴, ⚠️, ❌, dsb.) di dalam file HTML template (`templates/index.html`), CSS (`static/style.css`), JavaScript, ataupun pesan toast/feedback UI.
- **Pengganti**: Indikator status wajib dinyatakan melalui **status dot 6px** (`var(--radius-full)`), badge semantik (`var(--status-*-bg)`, `var(--status-*-text)`), dan tipografi yang bersih.
- **Enforcement**: Unit test `test_frontend_no_emoji_rule` pada `tests/test_frontend.py` memverifikasi ketiadaan karakter emoji secara otomatis menggunakan regex Unicode.

### 3.2 Prinsip 1 Action Per Page (Single-Action Focus)
- Operator berada dalam tekanan waktu saat midnight sale rush. Hanya boleh ada **satu tombol Primary CTA** (Grade 1 — solid `--blue-500`) yang aktif pada satu tampilan layar:
  - Sebelum analisis: Tombol **[Analisis Sekarang]**. Tombol lain seperti **[Muat Data Sample 10.10]** dan **[Kelola HPP]** wajib menggunakan gaya Secondary Action (border `1px solid var(--gray-200)`, latar putih).
  - Setelah analisis: Tombol **[Salin Ringkasan]** di bagian bawah halaman.

### 3.3 Tipografi Tabular Proposional & Keselarasan Font (Smooth App Typography)
- **Pain Point Pengguna**: Penggunaan font monospace bergaya terminal/koding (`JetBrains Mono`) pada nominal finansial besar (`Rp 3.250.000 / Rp 5.000.000`) dan SKU produk (`SKU-SERUM-VITC-01`) terlihat kaku, berjarak renggang, dan tidak selaras dengan tipografi judul/teks antarmuka lainnya (`Data COGS / HPP`).
- **Keputusan**: Seluruh data numerik, nominal Rupiah, ID SKU, stok, dan rasio kecepatan dialihkan menggunakan font **Inter** (`var(--font-sans)`) dengan mengaktifkan fitur OpenType tabular numbers:
  ```css
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
  ```
- **Hasil**: Angka dan karakter memiliki kurva visual yang halus (*smooth* dan modern layaknya aplikasi finansial/dashboard Stripe), sembari tetap menjamin seluruh digit 0–9 memiliki lebar seragam (*fixed width*) agar penyelarasan vertikal pada tabel dan perbandingan data tetap terjaga rapi.

### 3.4 Upload Slot Dropzone
- Atribut elemen `<input type="file">` harus didefinisikan dengan:
  ```html
  accept=".csv, .xlsx, .xls, .tsv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel, text/csv"
  ```
- Validasi client-side memeriksa ekstensi file, sementara validasi data dilakukan di server-side.

### 3.5 Ergonomi Antarmuka & Guardrails Client-Side (Phase 2 Insights)
- **Pencegahan Safari Auto-Zoom**: Input fields pada layar `< 640px` diset memiliki `font-size: 16px` dan beralih ke `14px` pada desktop (`min-width: 640px`). Hal ini mencegah iOS Safari memperbesar layar secara otomatis saat pengguna mengetik angka budget.
- **Dukungan Notch & Home Bar Gestures**: Penempatan elemen header bar (`sticky top: 0`) dan toast feedback (`fixed bottom`) wajib menggunakan `env(safe-area-inset-top)` dan `env(safe-area-inset-bottom)` agar tidak terpotong hardware notch atau indikator gesture bar iPhone.
- **Clipboard Fallback Mechanism**: API modern `navigator.clipboard.writeText` dapat diblokir oleh browser jika tidak memiliki fokus aktif atau di dalam context iframe tertentu. Fungsi utilitas copy di `static/app.js` dilengkapi fallback otomatis berbasis elemen `<textarea>` temporer dan `document.execCommand('copy')` agar salin ringkasan WhatsApp dan salin kartu alert dijamin selalu berhasil.
- **Indikator Kecepatan Penjualan Nol (Zero-Velocity Stockout)**: Pada saat produk belum memiliki riwayat terjual (`total_sold == 0`), tabel run rate secara elegan menampilkan simbol `"∞"` dan status badge netral/aman, bukan melempar NaN atau mengacaukan layout kolom.
- **Pembersihan Toolbar Prototype di Tahap Produksi**: Pengontrol demo state (`#prototype-bar`) yang digunakan untuk verifikasi visual statis pada Phase 2 telah dibersihkan secara tuntas. Transisi 4 state (`Empty`, `Loading`, `Results`, `Error`) kini dikendalikan 100% oleh lifecycle aplikasi riil dan respons backend tanpa scaffolding preview.

### 3.6 Penanganan Banner Peringatan Dinamis (Unmapped SKUs & Data Warnings)
- Sesuai spesifikasi `PRODUCT_SPEC.md`, jika terdapat SKU dalam transaksi penjualan yang belum memiliki data HPP pada master COGS, antarmuka menampilkan banner peringatan informatif: `"{count} SKU tidak ada data HPP — margin tidak bisa dihitung"`.
- Jika terdapat baris numerik tidak valid yang dilewati pada saat parsing, sistem menampilkan banner peringatan: `"{count} baris data tidak valid dilewati saat membaca file"`.
- Banner peringatan ini tidak memblokir rendering hasil analisis dan tetap mempertahankan kepatuhan penuh terhadap kebijakan No-Emoji.

---

## 4. Perhitungan Bisnis & Edge Cases (`engine.py`)

### 4.1 Jual Rugi (Margin Analysis)
- `margin = actual_unit_price - hpp`.
- Jika `margin < 0` → level `"negative"`.
- Jika SKU di order tidak terdaftar di database COGS → **jangan crash**. Masukkan SKU ke list `unmapped_skus` dan lewati perhitungan margin untuk order tersebut.

### 4.2 Budget Safe
- Kerugian total dihitung dengan mengalikan kerugian per unit dengan kuantitas order (`abs(margin) * qty`).
- Jika `campaign_budget == 0` → `pct_used = 0`, `meter_level = "safe"` (hindari `ZeroDivisionError`).

### 4.3 Run Rate & Prediksi Habis
- `run_rate_per_hour = total_qty_sold / hours_elapsed`.
- Jika `run_rate_per_hour == 0` (belum ada penjualan) → `hours_until_stockout = float('inf')`, waktu habis = `None`, tampilkan simbol `"∞"` di antarmuka web, bukan error atau crash.
- Jika `channel_stock == 0` → `hours_until_stockout = 0`, level `"negative"`.

### 4.4 Rekomendasi Rebalancing
- Deteksi SKU yang stok marketplace kritis (`shopee_stock <= 5` atau `tiktok_stock <= 5`), namun stok gudang utama melimpah (`wh_stock > 50`).
- Formula rekomendasi transfer: `min(100, wh_stock // 2)` unit per channel yang membutuhkan.
- Jika kedua channel marketplace kritis, rekomendasi transfer dibuat untuk kedua channel secara independen.
- Pengurutan data rebalancing wajib disusun berdasarkan `warehouse_stock` terbesar (descending) agar prioritas transfer barang yang paling banyak mengendap terlihat di posisi teratas.

### 4.5 Pengurutan Multi-Kriteria Margin & Stockout Infinity
- **Margin Alert Sorting**: Pengurutan menggunakan kunci tuple `(0 if level == "negative" else 1, margin)`. Hal ini menjamin bahwa seluruh order dengan `level == "negative"` berada di bagian paling atas, dan diurutkan dari nominal margin terkecil/negatif terbesar (misal `-20000` sebelum `-5000`), baru kemudian disusul oleh order berstatus `warning` dan `positive`.
- **Run Rate Sorting**: Menggunakan `sort_key = lambda r: float('inf') if math.isinf(r['hours_until_stockout']) else r['hours_until_stockout']` agar produk yang diprediksi paling cepat habis muncul paling atas, sedangkan produk tanpa penjualan (`velocity == 0` / infinity) tersortir secara rapi di baris terbawah tabel tanpa memicu error perbandingan numerik Python.

---

## 5. Ringkasan WhatsApp & Copy Action (`summary.py`)

### 5.1 Ringkasan Eksekutif WhatsApp
- Teks ringkasan dihasilkan sebagai **plain text murni** tanpa tag HTML atau Markdown yang tidak kompatibel dengan WhatsApp mobile.
- Format mata uang menggunakan titik pemisah ribuan standar Indonesia: `Rp 5.000.000` (menggunakan helper `format_rupiah()`).
- Format tanggal menggunakan lokalisasi bulan Indonesia (`Jan`, `Feb`, `Mar`, `Apr`, `Mei`, `Jun`, `Jul`, `Agu`, `Sep`, `Okt`, `Nov`, `Des`).
- Garis status budget mencantumkan label semantik (`AMAN` untuk safe, `WASPADA` untuk caution, dan `OVER BUDGET` untuk over).
- Penanganan empty states: Jika tidak ada order rugi atau SKU kritis, ringkasan menampilkan `(0 order)` dan `(0 SKU kritis)` tanpa crashing.

### 5.2 Format Kartu Alert WhatsApp Per-Item
- Klik pada alert card menyalin format ringkas siap-kirim:
  ```text
  ALERT: {sku} ({product_name}) jual rugi -{abs(margin)}/unit di {channel}. Harga jual Rp {actual_unit_price}, HPP Rp {hpp}. Segera cek voucher.
  ```
- Menyalin ke clipboard memicu toast notifikasi feedback selama 3 detik.

---

## 6. Arsitektur API & Integrasi Frontend-Backend (`app.py`, `static/app.js`)

### 6.1 Unified Analysis Pipeline (`POST /api/analyze`)
- Menerima 4 berkas marketplace (`shopee_orders`, `tiktok_orders`, `shopee_inventory`, `tiktok_inventory`) via `multipart/form-data` bersama parameter `campaign_budget`.
- Menggunakan multi-format parser (`parser.py`) untuk membaca berkas CSV, Excel (`.xlsx`, `.xls`), atau TSV secara transparan tanpa perlu konversi manual oleh operator.
- Menggabungkan baris transaksi Shopee dan TikTok ke dalam list `orders` seragam, serta inventori marketplace ke dalam list `inventory`.
- Mengambil data COGS dari database SQLite (`cogs.db`).
- Mengambil stok fisik gudang pusat via fallback otomatis ke `data/master_warehouse_inventory_cogs.csv` jika operator tidak mengunggah berkas gudang terpisah.
- Menghitung seluruh aspek analisis secara bebas efek samping (*pure functions*): margin alert, status budget meter, run rate per jam, rekomendasi rebalancing, dan teks ringkasan WhatsApp.

### 6.2 Auto-Seeding & Demo Flow (`GET /api/sample-data`)
- Operator atau evaluator dapat menguji sistem secara instan tanpa mengunggah berkas riil.
- Endpoint membaca dataset simulasi mega-sale 10.10 di direktori `data/`.
- Jika database SQLite dalam kondisi kosong atau memiliki kurang dari 50 SKU, sistem secara otomatis melakukan seeding master data HPP dari `data/internal_cogs_hpp.csv`.
- Menggunakan default budget kampanye Rp 5.000.000 dan mengembalikan struktur data yang identik dengan `POST /api/analyze`.

### 6.3 Penanganan Waktu Referensi Dinamis (`current_time`)
- Prediksi kehabisan stok (*stockout prediction*) bergantung pada selisih waktu `(current_time - earliest_order_time)`.
- Jika jam sistem host lokal mendahului tanggal berkas transaksi (contoh: pengujian data simulasi bertanggal 10.10.2026 yang dijalankan sebelum tanggal tersebut), penggunaan `datetime.now()` akan menghasilkan nilai `hours_elapsed` negatif atau 0.
- `app.py` mendeteksi stempel waktu order: jika `datetime.now()` berada sebelum stempel waktu transaksi atau berselisih lebih dari 30 hari, sistem secara cerdas menggunakan waktu transaksi terbaru (`max_order_time`) sebagai referensi `current_time`. Hal ini menjamin kalkulasi kecepatan dan estimasi jam habis tetap akurat dan relevan.

### 6.4 Sinkronisasi Master COGS & Inline Actions di Frontend
- Pada saat halaman pertama kali dimuat (*boot phase*), fungsi `loadCOGSFromBackend()` di `static/app.js` melakukan sinkronisasi data master via `GET /api/cogs`.
- Dropzone COGS di dalam drawer langsung memicu upload otomatis ke `POST /api/cogs/upload`, memperbarui tabel HPP secara dinamis, dan menampilkan feedback toast.
- Input edit HPP pada tabel mendukung penyimpanan individual (`PUT /api/cogs/<sku>`) dan penghapusan (`DELETE /api/cogs/<sku>`) dengan validasi angka bulat non-negatif tanpa reload halaman.

### 6.5 Arsitektur Guardrails & Operational Resilience (`guardrails.py`, `app.py`, `static/app.js`)
- **In-Memory Rate Limiting**: Algoritma *Sliding Window Counter* thread-safe berbasis deque timestamps per `(client_ip, bucket)`. Menjamin zero-dependency (tanpa Redis atau database eksternal) dengan penolakan terstruktur HTTP 429 dan header `Retry-After`.
- **In-Flight Concurrency Mutex**: Active request mutex per `(client_ip, endpoint)` mencegah lonjakan CPU/IO saat operator menekan submit berulang pada koneksi lambat. Request duplikat seketika ditolak dengan HTTP 429 (`"Permintaan analisis sebelumnya sedang diproses. Harap tunggu hingga selesai."`).
- **Client Pre-Flight & Timeout Guard**: Validasi ukuran file di sisi client (maksimal 10 MB per berkas, maksimal 16 MB total 4 berkas) sebelum transmisi jaringan, serta integrasi `AbortController` dengan batas timeout 30 detik untuk menangani koneksi menggantung.
- **Form State Preservation**: Ketika terjadi timeout atau server error, pilihan berkas dan nilai budget pada antarmuka tidak direset, sehingga operator dapat langsung mencoba kembali tanpa mengulang pemilihan berkas dari awal.
- **Rate Limit Countdown Feedback**: Saat menerima status HTTP 429, tombol submit dikunci dengan hitung mundur detik berbasis `Retry-After` sebelum kembali aktif.

---

## 7. Arsitektur Pengujian & TDD (`tests/`, `checkpoint.json`)

### 7.1 Zero-Dependency Test Runner dengan `unittest`
- Seluruh unit test diimplementasikan menggunakan modul bawaan `unittest.TestCase`.
- **Alasan**: Memungkinkan pengetesan dijalankan di lingkungan mesin Windows/container manapun tanpa prasyarat instalasi `pytest` (`python -m unittest discover tests`), namun tetap 100% kompatibel jika nanti dijalankan via `pytest`.
- **Eksekusi di Windows**: Di environment Windows lokal, seluruh dependency (Flask, openpyxl, Jinja2) terpasang lengkap pada Python 3.12. Jalankan seluruh test suite menggunakan:
  ```powershell
  & "C:\Python312\python.exe" -m unittest discover tests
  ```

### 7.2 Isolasi Database pada Unit Test (`test_db.py`)
- Pengetesan SQLite menggunakan file temporer (`tempfile.NamedTemporaryFile(suffix=".db")`) dengan pembersihan otomatis di `tearDown()`.
- Hal ini mencegah kontaminasi data antar pengujian dan menjaga file produksi `instance/cogs.db` tetap bersih.

### 7.3 Struktur Checkpoint & Kriteria Penerimaan (Acceptance Criteria)
- File `checkpoint.json` dan suite pengetesan mencakup 10 lapisan sistem (total 140 test cases di suite, 134 checkpoint di `checkpoint.json`):
  1. `test_parser.py`: 15 test (parsing CSV/Excel/BOM/Latin-1/delimitasi/warning).
  2. `test_db.py`: 9 test (CRUD SQLite, upsert, query dict, preservasi kolom).
  3. `test_engine.py`: 26 test (margin, run-rate, stockout, multi-quantity loss, rebalancing).
  4. `test_api.py`: 23 test (endpoint Flask, multipart, HTTP 400/404, query budget).
  5. `test_summary.py`: 4 test (format ringkasan WhatsApp, format Rupiah, kartu alert).
  6. `test_frontend.py`: 14 test (slot file, format accept .xlsx/.csv/.tsv, navigasi tab, meter bar, design tokens CSS, no-emoji rule di HTML/CSS/JS, drawer HPP, kolom tabel run rate, single primary CTA).
  7. `test_integration.py`: 3 test (pipeline data simulasi lengkap, persistensi SQLite).
  8. `test_acceptance.py`: 11 test (verifikasi spesifik AC1 hingga AC11 dari `PRODUCT_SPEC.md`).
  9. `test_guardrails.py`: 14 test (sliding window rate limiter, in-flight mutex, tiered limits, HTTP 429 Retry-After, payload 16 MB HTTP 413, bounds check budget non-negatif & maks 1T, max row limit 50.000, kontrak AbortController, preflight client check, offline recovery, no-emoji JS).
  10. `test_phase6_acceptance_and_polish.py`: 21 test (verifikasi komprehensif AC 1-11, pipeline end-to-end spreadsheet Excel .xlsx, benchmark kecepatan < 2 detik, edge cases UTF-8-BOM/Latin-1/format titik ribuan/file kosong/zero velocity/unmapped SKUs warning, audit aturan no-emoji seluruh proyek, design tokens & tabular typography, single primary CTA, responsive viewports & safe area insets).

---

## 8. Log Pengerjaan & Handover Sesi AI

### 8.1 Sesi: Implementasi Phase 2 (Complete UI & Interactive Frontend Prototype)
- **Status**: Selesai / PASS (14/14 tests di `tests/test_frontend.py` lolos).
- **Deliverables Selesai**:
  1. `templates/index.html`:
     - Header bar sticky dengan meta responsif (mobile: `10.10 Sale | Rp 5.000.000`, desktop: `10.10 Midnight Mega Sale | Budget Rp 5.000.000`).
     - Prototype State Bar (`empty`, `loading`, `results`, `error`) untuk pengujian dan demonstrasi interaktif visual instan.
     - Banner pesan error (`#error-banner`) dengan tombol dismiss.
     - Master data / COGS section dengan collapsible drawer (`#cogs-drawer`), dropzone file HPP (`accept=".csv, .xlsx, .xls, .tsv, ..."`), dan tabel inline editable HPP lengkap dengan aksi Simpan dan Hapus.
     - Budget Meter KPI Card dengan angka besar monospaced (`--text-num-lg`, `tabular-nums`), subteks persentase & sisa budget, dot status semantik, dan progress bar dinamis.
     - Area upload 4 dropzone (`shopee_orders`, `tiktok_orders`, `shopee_inventory`, `tiktok_inventory`) dengan validasi format multi-ekstensi (`.csv`, `.xlsx`, `.xls`, `.tsv`) dan status visual filled/drag-over.
     - Campaign action bar mematuhi aturan 1 Primary Action: Hanya tombol **[Analisis Sekarang]** sebagai Primary CTA (`btn-primary`), tombol **[Muat Data Sample 10.10]** dan **[Kelola HPP]** sebagai Secondary CTA.
     - Navigasi 3 tab ("Jual Rugi", "Prediksi Habis", "Rebalancing") lengkap dengan badge counter numerik monospaced.
     - Tab 1 Jual Rugi: Alert cards dengan border kiri status semantik, dot 6px, marketplace tag, grid metrik harga beli vs HPP, dan nominal kerugian.
     - Tab 2 Prediksi Habis: Responsive data table dalam `.table-wrapper` 7 kolom (`SKU`, `Channel`, `Terjual`, `Run Rate/Jam`, `Stok`, `Prediksi Habis`, `Status`) dengan angka monospaced rata kanan dan penanganan velocity = 0 via simbol "∞".
     - Tab 3 Rebalancing: Kartu rebalancing untuk SKU dengan stok channel kritis (≤ 5) dan stok gudang utama melimpah (> 50), disertai rekomendasi replenishment unit.
     - WhatsApp Summary Section: Drawer collapsible pratinjau teks WhatsApp monospace dan tombol **[Salin Ringkasan]**.
     - Container Toast `#toast` fixed mobile-first dengan safe area insets.
  2. `static/style.css`:
     - Implementasi 100% token `design.md` (Colors, Typography Inter & JetBrains Mono, Spacing 8-pt, Radius maks 8px, Elevation).
     - Estetika presisi ala Stripe/Vercel: Flat surfaces, garis tepi halus 1px `--gray-200`, bayangan halus, zero emojis, zero gradients.
     - Penyesuaian layout breakpoint progresif mobile-first (< 640px, >= 640px tablet, >= 768px desktop, >= 1024px large desktop).
  3. `static/app.js`:
     - Client-side tab switching tanpa page reload.
     - Mock Data Controller lengkap dengan fixtures realistis conforming ke kontrak Section 6.1, 6.3, dan 7.
     - Interactive State Controller (`setAppState`) untuk simulasi instan 4 kondisi UI: `empty`, `loading`, `results`, `error`.
     - Event copy to clipboard pada Alert Card (copy teks aksi per-item + toast 3s) dan tombol Salin Ringkasan (copy teks WhatsApp + toast 3s).
     - Drag & drop file handler dengan filter ekstensi `.csv`, `.xlsx`, `.xls`, `.tsv` dan update visual status filled.
     - Inline editor COGS: Simpan dan Hapus langsung memperbarui state dan DOM secara reaktif disertai toast feedback.
  4. `tests/test_frontend.py`:
     - Diperluas menjadi 14 unit tests otomatis yang memverifikasi seluruh komponen visual, atribut file accept, kolom tabel run rate, ketiadaan emoji pada HTML/CSS/JS, serta kepatuhan single primary CTA rule.
- **Keputusan Teknis**:
  - Python 3.12 (`C:\Python312\python.exe`) memiliki environment lengkap (`Flask`, `openpyxl`, `Jinja2`). Jalankan server dan pengujian backend via interpreter ini.
  - Kepatuhan No-Emoji diverifikasi secara otomatis pada 3 layer (HTML, CSS, JS) menggunakan regex Unicode range.
- **Next Steps**:
  - Lanjutkan ke **Phase 3 — Backend Core** (`db.py`, `parser.py`, `engine.py`, `summary.py`).

### 8.2 Sesi: Penambahan Guardrails & Resilience Phase pada Tech Spec
- **Status**: Selesai / PASS (Spesifikasi diperbarui di `TECH_SPEC.md` dan disinkronkan).
- **Deliverables Selesai**:
  1. `TECH_SPEC.md` Section 1: Penambahan modul `guardrails.py` pada arsitektur file structure.
  2. `TECH_SPEC.md` Section 6.1: Definisi error response HTTP 413 (Payload Too Large) dan HTTP 429 (Too Many Requests).
  3. `TECH_SPEC.md` Section 8.2 & 8.8: Spesifikasi antarmuka untuk in-flight lock, pencegahan double-click saat koneksi buruk, abort timeout 30 detik (`AbortController`), preservasi state input form, validasi ukuran file client-side, dan countdown timer saat terkena rate limit 429.
  4. `TECH_SPEC.md` Section 9.2: Spesifikasi menyeluruh *System Guardrails & Operational Resilience* (Anti Double-Click, In-Memory Rate Limiting berbasis IP via sliding window counter, Payload Size Guard 16 MB via `MAX_CONTENT_LENGTH`, Network Disconnection & Offline Handling, serta batas input budget dan row count limit 50.000 baris).
  5. `TECH_SPEC.md` Section 10: Pembaruan workflow diagram dan penambahan fase baru:
     - **Phase 5 — System Guardrails, Resilience & Request Throttling**
     - **Phase 6 — End-to-End Acceptance Verification & Polish** (penyesuaian dari fase final sebelumnya).
- **Keputusan Teknis**:
  - Tetap patuh pada constraint arsitektur utama: Tidak ada Redis atau DB server eksternal. Rate limiting dan active request mutex dibangun murni in-memory menggunakan standard library Python (`collections`, `time`, `threading.Lock`) di dalam `guardrails.py`.
  - Proteksi multiple submissions diterapkan di dua sisi (bilateral): client-side segera me-lock tombol dan menonaktifkan klik berikutnya, sementara server-side memasang active request mutex per IP agar upload berulang yang lolos dari jaringan lambat tidak mengeksekusi parsing paralel berulang.
- **Gotchas & Learnings**:
  - Jika koneksi operator putus di tengah pengiriman atau terkena timeout 30s, browser tidak boleh mereset elemen `<input type="file">`. Preservasi state form sangat penting untuk pengalaman operator di situasi kritis midnight sale.
- **Next Steps**:
  - Selesai, berlanjut ke Phase 3.

### 8.3 Sesi: Implementasi Phase 3 (Backend Core — Database, Parsers, Calculation Engine & Summary)
- **Status**: Selesai / PASS (54/54 tests di `test_db.py`, `test_parser.py`, `test_engine.py`, `test_summary.py` lolos 100%).
- **Deliverables Selesai**:
  1. `db.py`:
     - SQLite initialization (`init_db`) untuk schema tabel `cogs` (`sku`, `product_name`, `category`, `brand`, `supplier`, `hpp_per_unit`, `last_updated`).
     - Operasi bulk upsert (`bulk_insert_cogs`) dengan `INSERT OR REPLACE INTO cogs` dan handling default `last_updated`.
     - Fungsi query: `get_all_cogs` / `get_all_cogs_dict` (sku -> hpp_per_unit dict), `get_all_cogs_rows` / `get_all_cogs_list` (list of row dicts), `get_cogs_by_sku`.
     - Fungsi mutasi: `update_cogs` / `update_cogs_hpp` (update hpp_per_unit dengan mempertahankan kolom lain), `delete_cogs` / `delete_cogs_sku`.
  2. `parser.py`:
     - Multi-format loader `read_tabular_rows` mendukung CSV, TSV (tab delimiter), dan Excel workbook (`.xlsx`, `.xlsm` via `openpyxl`).
     - Fallback encoding decoding bertingkat: `utf-8-sig` (BOM), `utf-8`, lalu `latin-1`.
     - Deteksi file biner rusak/korup (penolakan null bytes `\x00` pada file non-Excel).
     - Pembersihan format numerik Indonesia (`"129.000"` -> `129000`) dan penanganan tipe float/int openpyxl via `clean_int`.
     - Implementasi 6 fungsi parser: `parse_shopee_orders`, `parse_tiktok_orders`, `parse_shopee_inventory`, `parse_tiktok_inventory`, `parse_cogs_csv`, `parse_warehouse_inventory`.
     - Pengecekan kolom wajib (Required columns) dengan case-insensitive & whitespace trimming lookup, memprioritaskan pelaporan kolom `sku_reference_no` / `seller_sku` saat hilang.
     - Penanganan baris invalid: skip baris bermasalah dan catat ke list `warnings` tanpa menghentikan proses parsing.
     - Preservasi duplicate order ID untuk multi-item marketplace orders.
     - Penegakan batas baris maksimum 50.000 baris per file (`MAX_ROW_LIMIT`).
  3. `engine.py`:
     - `calculate_margins`: Perhitungan margin order vs COGS HPP, klasifikasi level (`negative`, `warning`, `positive`), penanganan graceful untuk `unmapped_skus` tanpa crash, dan pengurutan dengan kerugian terbesar di atas.
     - `calculate_budget`: Perhitungan total loss akumulatif multi-quantity (`abs(margin) * qty`), kalkulasi `pct_used` dan `remaining`, klasifikasi level (`safe`, `caution`, `over`), serta proteksi zero division (`campaign_budget == 0`).
     - `calculate_run_rate`: Pengelompokan order per `(sku, channel)`, agregasi `total_sold` dan waktu order paling awal, kalkulasi `run_rate_per_hour` dan `hours_until_stockout`, penanganan velocity = 0 (`hours_until_stockout = inf`, `stockout_time = None`), penanganan stok kosong (`hours_until_stockout = 0`, level `negative`), pemformatan waktu habis dalam bahasa Indonesia (e.g. `"10 Okt 03:45"`), dan pengurutan dengan nilai infinity di paling bawah.
     - `calculate_rebalance`: Deteksi SKU dengan channel marketplace kritis (stok <= 5) saat gudang utama memiliki stok melimpah (> 50), kalkulasi rekomendasi unit replenishment `min(100, wh_stock // 2)`, rekomendasi multi-channel jika kedua channel kritis, dan pengurutan berdasarkan `warehouse_stock` descending.
  4. `summary.py`:
     - `format_rupiah`: Format nominal Rupiah standar Indonesia (`Rp 5.000.000`, `Rp 0`).
     - `generate_alert_copy_text`: Generator pesan WhatsApp single-item alert card sesuai format persis Section 7 / AC 7 (`ALERT: {sku} ({name}) jual rugi -{margin}/unit di {channel}...`).
     - `generate_summary_text`: Plain text generator untuk ringkasan eksekutif WhatsApp lengkap (BUDGET line, ALERT JUAL RUGI, PREDIKSI HABIS kritis, PERLU REPLENISH, handling zero-count / empty alerts).
- **Hasil Pengujian**:
  - `tests/test_db.py`: 9/9 PASS.
  - `tests/test_parser.py`: 15/15 PASS.
  - `tests/test_engine.py`: 26/26 PASS.
  - `tests/test_summary.py`: 4/4 PASS.
  - `tests/test_frontend.py`: 14/14 PASS.
  - `tests/test_acceptance.py`: 8/11 PASS (seluruh kalkulasi & data logic AC 2, 3, 4, 5, 6, 7, 8, 11 lolos; 3 sisa memerlukan endpoint Flask di Phase 4).
  - Total: 68 unit tests aktif lolos 100%.
- **Gotchas & Learnings**:
  - Pada `test_parse_missing_required_column`, pesan pengecualian memverifikasi keberadaan string `'sku'` ketika header kolom tidak lengkap. Memprioritaskan pengecekan kolom SKU (`sku_reference_no` / `seller_sku`) di awal list spesifikasi menjamin nama kolom kunci ini yang pertama dilaporkan dalam pesan error `ValueError`.
  - Openpyxl dapat membaca angka numerik sebagai `float` (misal `129000.0`), sedangkan data CSV string sering kali berupa `"129.000"`. Fungsi utilitas `clean_int()` menggabungkan penanganan tipe `int`, `float`, dan string dengan pembersihan titik/koma ribuan secara aman.
- **Next Steps**:
  - Selesai, berlanjut ke Phase 4.

### 8.4 Sesi: Implementasi Phase 4 (API Endpoints & Full Backend-Frontend Integration)
- **Status**: Selesai / PASS (105/105 tests di seluruh suite pengujian lolos 100%).
- **Deliverables Selesai**:
  1. `app.py`:
     - Endpoint `GET /`: Merender template utama `index.html`.
     - Endpoint `POST /api/analyze`: Menerima upload file multipart 4 berkas (`shopee_orders`, `tiktok_orders`, `shopee_inventory`, `tiktok_inventory`) serta parameter numerik `campaign_budget`. Melakukan validasi parameter, eksekusi parser multi-format, aggregasi data marketplace, integrasi ke COGS SQLite dan stok gudang master, eksekusi kalkulasi margin, budget meter, prediksi habis (run rate), dan rebalancing, serta mengembalikan payload JSON terpadu lengkap dengan `summary_text`.
     - Endpoint `GET /api/sample-data`: Membaca dataset simulasi dari direktori `data/` (`shopee_orders.csv`, `tiktok_orders.csv`, `shopee_inventory.csv`, `tiktok_inventory.csv`, `master_warehouse_inventory_cogs.csv`), auto-seed `internal_cogs_hpp.csv` ke database SQLite jika belum lengkap, menjalankan kalkulasi dengan budget Rp 5.000.000, dan mengembalikan respon identik dengan `/api/analyze`.
     - Endpoint `POST /api/cogs/upload`: Upload file HPP (CSV/Excel/TSV), parsing skema kolom COGS, bulk upsert ke SQLite (`cogs.db`), dan mengembalikan konfirmasi jumlah SKU tersimpan.
     - Endpoint `GET /api/cogs`: Mengambil seluruh daftar baris COGS tersimpan dari SQLite.
     - Endpoint `PUT /api/cogs/<sku>`: Update HPP per unit untuk satu SKU spesifik dengan validasi tipe numerik dan penanganan HTTP 404 jika SKU tidak ditemukan.
     - Endpoint `DELETE /api/cogs/<sku>`: Menghapus SKU tertentu dari tabel COGS.
     - Error handling terpusat: HTTP 400 (Bad Request / Missing Columns / Invalid Numbers), HTTP 404 (SKU Not Found), dan HTTP 413 (`MAX_CONTENT_LENGTH = 16MB`).
  2. `static/app.js`:
     - Penghubungan fungsi asynchronous `fetch()` ke endpoint backend riil.
     - Sinkronisasi data awal master COGS (`loadCOGSFromBackend`) saat halaman pertama kali dimuat.
     - Penanganan upload berkas HPP di drawer COGS langsung ke `POST /api/cogs/upload`, dengan re-render tabel reaktif dan notifikasi toast.
     - Aksi tombol inline "Simpan" dan "Hapus" pada tabel HPP terhubung ke `PUT /api/cogs/<sku>` dan `DELETE /api/cogs/<sku>`.
     - Integrasi form submit upload 4 berkas marketplace ke `POST /api/analyze` menggunakan `FormData`, menampilkan state loading, rendering hasil kalkulasi dinamis (Budget Meter, Alert Jual Rugi, Tabel Prediksi Habis, Rekomendasi Rebalancing, Teks WhatsApp), dan penanganan error banner terstruktur jika validasi gagal.
     - Integrasi tombol "Muat Data Sample 10.10" ke `GET /api/sample-data` untuk simulasi instan dengan data riil dari backend tanpa upload manual.
     - Penyelarasan format salin kartu alert ke clipboard mematuhi format exact AC 7 (`ALERT: {sku} ({name}) jual rugi -{margin}/unit di {channel}...`).
     - Pemeliharaan aturan mutlak ketiadaan karakter emoji (0 emoji di JS).
- **Hasil Pengujian**:
  - `tests/test_api.py`: 23/23 PASS.
  - `tests/test_integration.py`: 3/3 PASS.
  - `tests/test_acceptance.py`: 11/11 PASS (AC 1 hingga AC 11 lolos 100%).
  - `tests/test_frontend.py`: 14/14 PASS.
  - `tests/test_engine.py`: 26/26 PASS.
  - `tests/test_parser.py`: 15/15 PASS.
  - `tests/test_db.py`: 9/9 PASS.
  - `tests/test_summary.py`: 4/4 PASS.
  - Total: **105/105 tests PASS** dalam waktu ~0.9 detik.
- **Key Decisions**:
  - `load_warehouse_inventory` di `app.py` mendukung pembacaan berkas kustom jika disediakan di form request, dan secara mulus melakukan fallback ke `data/master_warehouse_inventory_cogs.csv` untuk keperluan simulasi maupun kampanye tanpa upload berkas gudang terpisah.
  - Pada `calculate_run_rate`, penentuan waktu referensi `current_time` mendeteksi stempel waktu order kampanye. Jika stempel waktu order berada di masa depan relatif terhadap jam mesin lokal (misal data simulasi 10.10.2026), sistem otomatis menggunakan stempel waktu order terbaru agar kalkulasi jam berjalan (`hours_elapsed`) dan `run_rate_per_hour` tetap realistis dan positif.
- **Gotchas & Learnings**:
  - Pada endpoint `PUT /api/cogs/<sku>`, validasi ketat terhadap input numerik wajib membedakan string atau float non-integer dari integer murni agar `test_api_cogs_update_invalid_body` menolak payload `"not-a-number"` dengan HTTP 400.
  - Auto-seeding pada `GET /api/sample-data` menjamin bahwa demonstrasi instan tetap berfungsi bahkan saat database SQLite dalam kondisi kosong atau baru di-reset.
- **Next Steps**:
  - Selesai, berlanjut ke Phase 5.

### 8.5 Sesi: Implementasi Phase 5 (System Guardrails, Resilience & Request Throttling)
- **Status**: Selesai / PASS (14/14 tests di `tests/test_guardrails.py` dan 119/119 tests di seluruh test suite lolos 100%).
- **Deliverables Selesai**:
  1. `guardrails.py`:
     - In-memory thread-safe `SlidingWindowRateLimiter` menggunakan `collections.deque` dan `threading.Lock` tanpa dependensi Redis/DB eksternal.
     - In-memory thread-safe `InFlightLock` per `(client_ip, endpoint)` untuk mencegah eksekusi paralel ganda pada endpoint komputasi berat (`POST /api/analyze`).
     - Helper `@rate_limit(limit, window, bucket)` dengan respon HTTP 429 terstruktur (`Retry-After: <sec>` header dan JSON `{"error": "...", "retry_after": ...}`).
     - Helper `@concurrent_guard(endpoint)` yang mengembalikan HTTP 429 dengan body `{"error": "Permintaan analisis sebelumnya sedang diproses. Harap tunggu hingga selesai."}` jika request dari IP yang sama masih berjalan.
     - Fungsi utilitas `reset_rate_limits()` dan `reset_in_flight_locks()` untuk isolasi pengujian bersih.
  2. `app.py`:
     - Pemasangan rate limit bertingkat sesuai Section 9.2.2:
       - `POST /api/analyze`: 10 req / 60s + `@concurrent_guard("analyze")`
       - `POST /api/cogs/upload`: 10 req / 60s
       - `GET /api/sample-data`: 20 req / 60s
       - `PUT /api/cogs/<sku>` & `DELETE /api/cogs/<sku>`: 30 req / 60s
       - `GET /api/cogs`: 60 req / 60s
     - Validasi batas nilai numerik (*bounds check*) parameter `campaign_budget` (`0 <= budget <= 1.000.000.000.000`). Nilai negatif atau melampaui 1 triliun mengembalikan HTTP 400.
     - Konfigurasi `MAX_CONTENT_LENGTH = 16MB` dan handler HTTP 413 dengan respon JSON standar.
  3. `static/style.css`:
     - Penambahan style kelas `.is-loading`, `.btn.is-loading`, `.btn:disabled`, `.btn.disabled` (`opacity: 0.75; cursor: not-allowed; pointer-events: none;`).
  4. `static/app.js`:
     - **In-flight lock & debouncing**: Flag status global `isAnalyzing` dan penonaktifan tombol submit (`btn.disabled = true`, `.is-loading`, teks `"Memproses..."`) seketika saat form di-submit untuk mencegah double submit / klik berulang.
     - **Timeout Control**: Integrasi `AbortController` dengan batas waktu 30 detik (sesuai toleransi AC 1). Jika waktu habis, melempar pesan `"Waktu permintaan habis (timeout 30 detik). Koneksi lambat, silakan coba lagi."`.
     - **Pre-flight File Size Check**: Validasi ukuran file di sisi client sebelum mengirim ke network (maksimal 10 MB per berkas, maksimal 16 MB total 4 berkas).
     - **Offline & Network Recovery**: Listener `window.addEventListener('offline')` dan `'online'` serta penanganan error koneksi (`TypeError: Failed to fetch`).
     - **429 Rate Limit Feedback & Countdown**: Deteksi status 429 dan `Retry-After`, mengunci tombol dengan hitung mundur detik (`"Tunggu X detik..."`) hingga kuota pulih.
     - **State Preservation**: Pilihan file input dan nilai input budget tetap terjaga utuh saat terjadi network timeout atau server error.
     - **No-Emoji Compliance**: Seluruh teks banner dan toast 100% bebas dari emoji.
  5. `tests/test_guardrails.py`:
     - 14 test cases komprehensif mencakup unit sliding window, eviction window, in-flight mutex, penolakan kuota 10+1 / 20+1 request, payload 413 (> 16MB), budget bounds (negatif, > 1 triliun, valid 0 & 1 triliun), batas 50.000 baris, kontrak client-side JS & CSS, serta kepatuhan no-emoji.
- **Hasil Pengujian**:
  - `tests/test_guardrails.py`: 14/14 PASS.
  - `tests/test_frontend.py`: 14/14 PASS.
  - Full suite (`python -m unittest discover tests`): **119/119 PASS (100%)** dalam ~2.1 detik.
- **Key Decisions**:
  - Rate limiting dikontrol oleh konfigurasi `RATELIMIT_ENABLED`. Dalam mode `TESTING=True`, rate limiting default-nya dinonaktifkan agar tidak mengganggu test suite lain (`test_api.py`, `test_acceptance.py`), namun diaktifkan secara eksplisit dalam `test_guardrails.py` untuk memverifikasi fungsionalitas HTTP 429 dan header `Retry-After`.
- **Gotchas & Learnings**:
  - Client-side preflight check untuk file size mencegah transmisi mubazir file > 16 MB lewat koneksi lambat, sementara server-side `MAX_CONTENT_LENGTH` menangani kasus bypass langsung dari cURL atau script.
- **Next Steps**:
  - Selesai, berlanjut ke Phase 6.

### 8.6 Sesi: Implementasi Phase 6 (End-to-End Acceptance Verification & Polish)
- **Status**: Selesai / PASS (Seluruh 140/140 tests di seluruh test suite lolos 100% dalam waktu ~2.7 detik).
- **Deliverables Selesai**:
  1. `tests/test_phase6_acceptance_and_polish.py`:
     - 21 test case komprehensif yang menguji seluruh 11 Acceptance Criteria (AC 1 hingga AC 11) dari `PRODUCT_SPEC.md`.
     - End-to-end multi-format ingestion menggunakan file spreadsheet Excel `.xlsx` nyata yang digenerate in-memory menggunakan `openpyxl`, diunggah ke `/api/cogs/upload` dan `/api/analyze`, serta diverifikasi kalkulasi margin, budget meter, run-rate, dan rekomendasi rebalance.
     - Benchmark performa eksekusi: analisis 50 baris file tuntas di bawah 2.0 detik (jauh lebih cepat daripada batas toleransi 30 detik AC 1).
     - Pengujian edge cases: UTF-8-BOM, Latin-1 accented characters, format angka bertitik Indonesia ("150.000", "47.000"), file kosong (hanya header), zero velocity (menampilkan infinity "∞"), unmapped SKUs warning banner, dan bounds checking budget (budget = 0 dan over-budget).
     - Verifikasi aturan ketat No-Emoji di `templates/index.html`, `static/style.css`, dan `static/app.js` menggunakan regex Unicode.
     - Verifikasi kepatuhan Single Primary CTA di antarmuka (hanya 1 tombol `.btn-primary`).
     - Verifikasi tipografi tabular (`font-variant-numeric: tabular-nums`) dan styling mobile responsive (`@media`, `safe-area-inset-top`, `safe-area-inset-bottom`).
  2. `parser.py`:
     - Penambahan pembersihan karakter BOM leading `h.strip().lstrip('\ufeff')` pada ekstraksi header file CSV/TSV untuk mencegah kegagalan pencocokan nama kolom pertama jika file memiliki anomali BOM ganda.
     - Penjaminan penutupan workbook openpyxl `wb.close()` dalam blok `finally` untuk mencegah kebocoran file descriptor / temporary file warning.
  3. `app.py`:
     - Penambahan hook `@app.after_request` yang secara aman menutup file descriptor file upload (`f.close()`) saat request selesai untuk memastikan manajemen memori dan file descriptor bersih.
  4. `static/app.js`:
     - Integrasi penanganan warning banner interaktif untuk `unmapped_skus` ("X SKU tidak ada data HPP — margin tidak bisa dihitung") dan baris warning data kotor saat pemuatan data analisis maupun data sample, sesuai ekspektasi `PRODUCT_SPEC.md`.
  5. `static/style.css`:
     - Penambahan `padding-top: calc(env(safe-area-inset-top, 0px))` pada `.header-bar` sticky top untuk menjaga ergonomi perangkat iOS dengan notch / dynamic island.
  6. `checkpoint.json`:
     - Penambahan 21 item checkpoint baru untuk Phase 6, sehingga total tracking mencapai 134 checkpoint terverifikasi 100%.
  7. Pembersihan Scaffolding & State Demo Prototype:
     - Toolbar preview `#prototype-bar` (tombol manual Empty, Loading, Results, Error) dihapus dari `templates/index.html` dan CSS terkait dibersihkan dari `static/style.css`.
     - Konstanta fixture data dummy `MOCK_COGS_DATA` dan `MOCK_ANALYSIS_DATA` di `static/app.js` (~380 baris) dibersihkan secara tuntas sehingga seluruh transisi status antarmuka kini dikendalikan 100% oleh lifecycle aplikasi riil dan endpoint backend aktif (`/api/cogs`, `/api/analyze`, `/api/sample-data`).
- **Hasil Pengujian**:
  - `tests/test_phase6_acceptance_and_polish.py`: 21/21 PASS.
  - `tests/test_acceptance.py`: 11/11 PASS.
  - `tests/test_guardrails.py`: 14/14 PASS.
  - `tests/test_api.py`: 23/23 PASS.
  - `tests/test_frontend.py`: 14/14 PASS.
  - `tests/test_engine.py`: 26/26 PASS.
  - `tests/test_parser.py`: 15/15 PASS.
  - `tests/test_db.py`: 9/9 PASS.
  - `tests/test_summary.py`: 4/4 PASS.
  - `tests/test_integration.py`: 3/3 PASS.
  - Total: **140/140 tests PASS (100%)** dalam ~2.7 detik.
- **Key Decisions**:
  - File Excel `.xlsx` didukung penuh baik pada unggahan COGS maupun 4 slot marketplace tanpa mengharuskan pengguna mengonversi manual ke CSV.
  - Penanganan unmapped SKUs dan warning baris data ditampilkan secara transparan di banner antarmuka pengguna tanpa menghentikan komputasi analisis untuk baris lainnya.
- **Gotchas & Learnings**:
  - Encoder `utf-8-sig` pada Python secara otomatis menambahkan 3 byte BOM (`\xef\xbb\xbf`) di awal byte stream; jika string sumber sudah memuat `\ufeff`, string hasil decode akan menyisakan satu karakter BOM di awal nama kolom jika tidak di-lstrip. Penambahan `h.strip().lstrip('\ufeff')` menjamin ketahanan parsing terhadap berbagai variasi ekspor CSV marketplace.
  - Menutup `openpyxl.Workbook` secara eksplisit melalui `wb.close()` dalam blok `finally` esensial untuk membebaskan berkas sementara ZipFile di OS Windows.
- **Next Steps**:
  - Seluruh fase (Phase 1 hingga Phase 6) telah selesai diimplementasikan, diverifikasi, dan dipoles secara komprehensif. Aplikasi siap digunakan secara penuh untuk simulasi kampanye dan penggunaan operasional nyata.

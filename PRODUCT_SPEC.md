# 📋 PRODUCT_SPEC.md — SIRCLO Marketplace Monitor
> UX, States & User Journey

---

## 1. North Star & User Context

**User**: Operator Brand AM — mengelola 4 brand beauty & fashion di Shopee + TikTok Shop.

**Situasi**: Midnight mega-sale campaign (10.10). Order membludak. Voucher numpuk. Stok habis di satu channel tapi warehouse masih penuh.

**Pain saat ini**: Setiap jam, operator harus download file laporan (CSV atau Excel) dari 2 seller center, gabung manual di Google Sheets/Excel, pakai formula untuk cari mana yang rugi dan kapan stok habis. Total **~45 menit per cycle**. Saat midnight rush, ini terlalu lambat — keputusan telat = kerugian bertambah.

**Target**: Upload file (CSV, Excel `.xlsx`/`.xls`, dsb.) → **hasil analisis instan**. Operator langsung tahu mana yang harus di-delist, di-replenish, atau dibiarkan.

---

## 2. 1-Flow User Journey

**Input → Trigger → Action**

### Step 1 — Input
Operator upload 4 file data (format CSV, Excel `.xlsx` / `.xls`, atau format tabular serupa seperti `.tsv`) ke slot masing-masing:
- Shopee Orders
- TikTok Orders
- Shopee Stok
- TikTok Stok

Data HPP sudah tersimpan di sistem (upload pertama kali via file CSV/Excel, editable kapan saja).

Campaign budget di-set sekali di awal (nama campaign + total budget voucher yang bisa "rugi").

### Step 2 — Trigger
Tekan **[ 📊 Analisis Sekarang ]**.

Sistem join semua data via SKU, hitung margin per order, run rate per jam, dan cek keseimbangan stok — selesai dalam hitungan detik.

### Step 3 — Action
Operator lihat hasilnya di 3 area:

1. **Budget Meter** (atas) — total kerugian voucher vs budget campaign. Hijau / kuning / merah.
2. **Alert Cards** (tengah, 3 tab):
   - **Jual Rugi**: Order dimana harga jual setelah semua diskon < HPP
   - **Prediksi Habis**: Run rate per SKU → jam berapa stok habis
   - **Rebalancing**: Channel kosong tapi warehouse masih ada ratusan unit
3. **Ringkasan WA** (bawah) — tombol "Salin Ringkasan" → copy summary text ke clipboard, siap paste ke grup WA manager.

Klik alert card → pesan aksi per-item ter-copy ke clipboard, siap paste ke grup WA tim.

---

## 3. UX States

### Empty
Pertama kali buka: instruksi singkat, slot upload kosong, dan tombol **[ Muat Data Sample 10.10 ]** supaya bisa coba tanpa upload file asli.

### Loading
Setelah klik Analisis: indikator proses. Target < 2 detik. Kalau lewat 5 detik, muncul pesan "Memproses..."

### Results
Alert cards muncul dengan badge warna:
- 🔴 Merah — perlu aksi segera (jual rugi / stok habis < 2 jam)
- 🟡 Kuning — warning (margin tipis / stok menipis)  
- 🟢 Hijau — aman

Sorted: yang paling kritis di atas.

### Feedback
- Klik card → "Pesan aksi disalin" (toast 3 detik)
- Salin Ringkasan → "Ringkasan disalin ke clipboard" (toast 3 detik)

### Error
- Format file tidak didukung / kolom salah → "❌ Kolom 'sku_reference_no' tidak ditemukan di file Shopee Orders" atau "❌ Format file tidak didukung. Harap upload CSV atau Excel (.xlsx/.xls)"
- SKU di order tapi tidak ada di data HPP → "⚠️ 3 SKU tidak ada data HPP — margin tidak bisa dihitung"
- Run rate nol (belum ada penjualan) → tampilkan "∞" untuk prediksi habis, bukan crash

---

## 4. Acceptance Criteria

| # | Kriteria |
|---|---|
| 1 | Upload 4 file (CSV, Excel `.xlsx`/`.xls`, dsb.) + klik Analisis → hasil muncul dalam < 30 detik (termasuk waktu upload) |
| 2 | Semua order dengan harga jual aktual < HPP terdeteksi dan muncul di tab Jual Rugi |
| 3 | Run rate = total terjual ÷ jam berjalan — akurat vs hitung manual |
| 4 | Prediksi habis = stok sisa ÷ run rate — toleransi ± 15 menit |
| 5 | Budget meter = sum seluruh kerugian order yang jual di bawah HPP |
| 6 | SKU dengan stok marketplace ≤ 5 dan warehouse > 50 muncul di tab Rebalancing |
| 7 | Klik alert card → clipboard berisi pesan aksi yang sesuai |
| 8 | "Salin Ringkasan" → clipboard berisi summary text lengkap: overview, top rugi, top habis, rebalancing, budget |
| 9 | Data HPP persist setelah upload pertama — tidak hilang saat refresh |
| 10 | Tombol "Muat Data Sample" berfungsi tanpa upload file |
| 11 | SKU tanpa penjualan (velocity = 0) → prediksi habis = "∞", bukan error |

---

## 5. Boundaries

**Yang TIDAK termasuk scope ini:**
- Koneksi API marketplace (download manual sudah cukup cepat)
- Login / multi-user / roles
- Tokopedia (nanti, fokus 2 channel dulu)
- Bot otomatis delist/replenish
- Database server — cukup penyimpanan ringan
- Analisis historis / trend

---

## 6. Context & Session Continuity

Pengembangan project ini dikerjakan secara bertahap melalui berbagai sesi kerja AI (Antigravity). Untuk menjaga kesinambungan konteks dan mencegah hilangnya progress ataupun detail teknis antar sesi:
- File `learnings.md` di root directory digunakan sebagai catatan hidup (*living memory*) untuk mencatat progress, keputusan teknis, gotchas, dan rencana langkah selanjutnya.
- Setiap sesi baru wajib membaca `learnings.md` di awal sesi dan mengisinya dengan hasil kerja sebelum sesi berakhir.
- Rincian protokol kontinuitas sesi didefinisikan secara lengkap di `TECH_SPEC.md` (*AI Session Continuity Protocol*).


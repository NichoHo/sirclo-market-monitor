# design.md — UI Tokens & Mobile-First Design System
> SIRCLO Marketplace Monitor

Semua nilai di bawah bersifat **exact** dan menjadi sumber kebenaran tunggal (*single source of truth*) untuk implementasi antarmuka web. Seluruh nilai token, warna, tipografi, ukuran, dan aturan interaksi wajib diimplementasikan persis seperti tertulis.

**Referensi Visual**: Stripe Dashboard, Vercel Dashboard, GitHub Mobile.  
**Karakter Estetika**: Bersih, presisi tinggi, banyak *white space* terukur, tipografi rapi, palet warna muted dan fungsional, serta permukaan datar (*flat surfaces*) dengan elevasi border 1px dan bayangan halus. **Sama sekali tidak menggunakan emoji, tidak ada gradien, dan tidak ada dekorasi visual tanpa fungsi.**

---

## 1. Filosofi & Prinsip Desain (Core Design Principles)

### 1.1 Mobile-First Architecture & Ergonomics
Antarmuka dirancang dari layar ponsel pintar (*mobile screen* 360px–430px) sebagai baseline utama, kemudian diperluas secara progresif (*progressive enhancement*) ke layar tablet (`min-width: 640px`) dan desktop (`min-width: 1024px`).

1. **Mobile Baseline**: Semua aturan CSS dasar ditulis tanpa *media query* untuk melayani perangkat mobile terlebih dahulu. Penyesuaian layar yang lebih lebar wajib menggunakan `@media (min-width: ...)` (skalabilitas mobile-first ke atas), bukan `@media (max-width: ...)` (desktop-down).
2. **Touch Targets (Standar Kenyamanan Jari)**:
   - Semua elemen yang dapat diklik atau disentuh (tombol, tab, slot upload, alert card, input form) memiliki ukuran area sentuh minimal **44 × 44 px** (sesuai standar *Apple Human Interface Guidelines* dan *Material Design*).
   - Jarak antar-elemen interaktif minimal `8px` (`--space-2`) untuk mencegah salah sentuh (*accidental tap*).
3. **Ergonomi Zona Jempol (Thumb-Zone Optimization)**:
   - Kontrol utama, tombol pemicu analisis, navigasi tab, dan tombol salin ringkasan diletakkan di area tengah hingga bawah layar agar dapat dioperasikan nyaman menggunakan satu tangan.
4. **Dukungan Layar Penuh (Safe Area Insets)**:
   - Komponen yang menempel di tepi layar (Header bar, Toast notification, Sticky bottom action) wajib memperhitungkan notch dan home bar gesture via `env(safe-area-inset-top)` dan `env(safe-area-inset-bottom)`.
5. **Pencegahan Safari Auto-Zoom**:
   - Ukuran font pada elemen `<input>` dan `<select>` pada viewport mobile diset minimal `16px` (atau disesuaikan dengan scale viewport) agar browser iOS tidak melakukan auto-zoom yang mengacaukan layout saat pengguna mengetik.
6. **Mobile Table Adaptability**:
   - Tabel data multi-kolom dibungkus dalam `.table-wrapper` dengan *horizontal smooth scrolling* (`-webkit-overflow-scrolling: touch`) dan bayangan indikator overflow, sehingga tidak pernah merusak lebar halaman smartphone.

---

### 1.2 Prinsip 1 Action Per Page / Screen (Single-Action Focus)
Saat operator menghadapi situasi genting midnight sale (10.10 mega-sale), beban kognitif (*cognitive load*) harus ditekan serendah mungkin. Operator tidak boleh mengalami keraguan atau kebingungan memilih tombol.

1. **Aturan 1 Primary CTA**:
   - Pada setiap fase atau status layar, **HANYA ADA TEPAT SATU TOMBOL UTAMA (Primary CTA)** yang memiliki bobot visual tertinggi (*solid accent background*).
   - **Fase 1: Input & Setup (Sebelum Analisis)**:
     - **Primary Action**: **[Analisis Sekarang]** (Latar solid `--blue-500`, teks putih, font-weight 600, lebar penuh 100% pada mobile, tinggi minimal 44px).
     - **Secondary Actions**: Tombol pendukung seperti **[Muat Data Sample 10.10]** dan **[Kelola HPP]** menggunakan gaya *Secondary Action* (latar putih, border 1px solid `--gray-200`, teks `--gray-700`). Keduanya tidak boleh mencuri perhatian visual dari tombol Analisis.
   - **Fase 2: Hasil & Eksekusi (Setelah Analisis Selesai)**:
     - Fokus operator beralih dari upload ke aksi penyebaran informasi dan mitigasi rugi.
     - **Primary Action Global**: **[Salin Ringkasan]** di bagian bawah halaman (atau bar aksi bawah) untuk menyalin laporan terformat ke grup WhatsApp manajemen.
     - **Primary Action Kontekstual (Per Item)**: Mengetuk satu baris Alert Card untuk langsung menyalin rekomendasi tindakan per SKU ke clipboard.
2. **Matriks Hirarki Aksi**:
   - **Grade 1 — Primary Action**: Latar `--blue-500`, hover `--blue-600`, teks `--white`, radius `--radius-md`, tinggi minimal 44px. Maksimal 1 per viewport.
   - **Grade 2 — Secondary Action**: Latar `--white`, border `1px solid var(--gray-200)`, hover `--gray-50`, teks `--gray-700`, radius `--radius-md`, tinggi minimal 44px pada mobile.
   - **Grade 3 — Utility / Ghost Action**: Latar transparan, tanpa border, teks `--gray-600`, hover `--gray-100`. Digunakan untuk tab, accordion toggle, atau dismiss action.

---

### 1.3 Sistem Spacing & Irama Ruang (8-Point Grid & Gestalt Proximity)
1. **Mathematical 8-Point Scale**:
   - Seluruh margin, padding, gap flexbox/grid, dan tinggi komponen diturunkan dari kelipatan dasar 4px dan 8px (`4px`, `8px`, `12px`, `16px`, `20px`, `24px`, `32px`, `40px`).
2. **Hukum Kedekatan Ruang (Gestalt Law of Proximity)**:
   - **Micro Spacing (4px–8px)**: Elemen yang berpasangan secara semantik (ikon + teks, dot status + overline label, badge padding internal, label input ke field input).
   - **Component Internal Spacing (12px–16px)**: Jarak antar-elemen di dalam kartu, padding dalam kartu pada mobile, celah antar-kolom form input.
   - **Section Separation Spacing (20px pada mobile, 24px–32px pada desktop)**: Jarak pemisah antar-modul utama (Header ke Budget Meter, Budget Meter ke Upload Area, Upload ke Tab Nav, Tab Nav ke Content Area, Content ke Action Footer).
3. **Responsive Gutters**:
   - Gutter container pada mobile adalah `16px` (`--space-4`) untuk memaksimalkan area baca di layar sempit.
   - Gutter container pada desktop melebar menjadi `24px` (`--space-6`) untuk memberikan kesan lapang dan elegan ala Stripe Dashboard.

---

### 1.4 Tipografi & Kejelasan Numerik (Typography & Tabular Numerics)
1. **Dual-Typeface System**:
   - `--font-sans`: Digunakan untuk seluruh teks UI, judul, paragraf, label form, tombol, dan tab navigation. Menggunakan font Inter yang bersih dan mudah dibaca pada layar kecil.
   - `--font-mono`: Wajib digunakan untuk seluruh data finansial mata uang Rupiah, SKU produk, angka stok, kecepatan penjualan (*run rate*), persentase, dan waktu.
2. **Tabular Numerics Rule**:
   - Seluruh angka data finansial dan numerik wajib menerapkan `font-variant-numeric: tabular-nums` (font monospaced angka) agar seluruh digit memiliki lebar seragam (*fixed width*). Ini memastikan angka ribuan, ratusan, dan tanda desimal sejajar secara vertikal saat dibandingkan.
3. **Format Standar Data Finansial & Metrik**:
   - Mata uang: `Rp 5.000.000` (menggunakan titik sebagai pemisah ribuan, spasi setelah simbol Rp).
   - Nilai negatif: `-Rp 25.000` (tanda minus sebelum Rp, diwarnai `--status-negative-text`).
   - Persentase: `65%` (tanpa spasi antara angka dan simbol persen).
   - Kecepatan penjualan: `12.5/jam`.
4. **Kepatuhan Aksesibilitas Kontras (WCAG 2.1 AA)**:
   - Teks body dan label memiliki rasio kontras minimal **4.5:1** terhadap latar belakang (`--gray-700` atau `--gray-800` di atas `--white` / `--gray-50`).
   - Teks judul besar memiliki rasio kontras minimal **3:1** terhadap latar belakang.

---

### 1.5 Konsistensi Visual Seluruh Aplikasi
1. Seluruh kartu, container, dan panel menggunakan latar belakang solid putih (`--white`) atau `--gray-50`, dibatasi garis tepi halus `1px solid var(--gray-200)`.
2. Sudut melengkung (*border radius*) dibatasi maksimal `8px` (`--radius-lg`). Tidak diperbolehkan sudut melengkung besar yang berlebihan.
3. Status operasional selalu dinyatakan melalui kombinasi warna latar muted, teks kontras tinggi, dan titik indikator lingkaran 6px (`--radius-full`), bukan dengan warna mencolok berlebihan.

---

## 2. Color Palette (Palet Warna Exact)

Semua token warna di bawah ini bersifat fixed. Dilarang menggunakan kode HEX di luar daftar ini.

### 2.1 Base Grayscale

| Token | Hex | Rasio Kontras ke Putih | Penggunaan Utama |
|---|---|---|---|
| `--gray-50` | `#FAFAFA` | 1.05:1 | Background utama halaman web, table header background |
| `--gray-100` | `#F4F4F5` | 1.16:1 | Background section, hover row tabel, tag marketplace |
| `--gray-200` | `#E4E4E7` | 1.35:1 | Border card default, garis separator tabel, tab divider |
| `--gray-300` | `#D4D4D8` | 1.68:1 | Border input saat idle, border upload slot default |
| `--gray-400` | `#A1A1AA` | 2.50:1 | Placeholder input, upload slot hint text |
| `--gray-500` | `#71717A` | 4.61:1 (Lolos AA) | Teks secondary, label overline, tab inactive |
| `--gray-600` | `#52525B` | 6.84:1 (Lolos AA) | Teks label form, badge label neutral |
| `--gray-700` | `#3F3F46` | 9.42:1 (Lolos AAA) | Teks body utama, table cell text, secondary button text |
| `--gray-800` | `#27272A` | 12.8:1 (Lolos AAA) | Teks heading, nama produk pada alert card |
| `--gray-900` | `#18181B` | 16.1:1 (Lolos AAA) | Header bar background, toast background, active tab text |
| `--white` | `#FFFFFF` | - | Card surface, background dropdown, input surface |

---

### 2.2 Accent Colors

| Token | Hex | Penggunaan Utama |
|---|---|---|
| `--blue-500` | `#3B82F6` | Tombol Primary (Grade 1 CTA), link aktif, border upload active/filled |
| `--blue-600` | `#2563EB` | Tombol Primary saat hover / pointer interaction |
| `--blue-50` | `#EFF6FF` | Background upload slot saat drag-over dan filled |

---

### 2.3 Semantic Status Palette

Digunakan untuk alert card, badge status, dan dot indikator operasional:

| Status Token | Background (`-bg`) | Text/Border (`-text`) | Dot (`-dot`) | Penggunaan Semantik |
|---|---|---|---|---|
| `--status-negative` | `#FEF2F2` | `#991B1B` | `#DC2626` | Jual rugi, stok kritis (< 2 jam habis), error sistem |
| `--status-warning` | `#FFFBEB` | `#92400E` | `#D97706` | Margin tipis, stok menipis (2–4 jam habis), peringatan |
| `--status-positive` | `#F0FDF4` | `#166534` | `#16A34A` | Profit aman, stok cukup (> 4 jam), proses selesai |
| `--status-neutral` | `#F4F4F5` | `#3F3F46` | `#71717A` | Belum ada data analisis, idle, counter 0 |

---

### 2.4 Budget Meter Palette

| Token | Hex | Kondisi Penggunaan |
|---|---|---|
| `--meter-safe` | `#16A34A` | Kerugian voucher 0%–50% dari budget campaign |
| `--meter-caution` | `#D97706` | Kerugian voucher 51%–80% dari budget campaign |
| `--meter-over` | `#DC2626` | Kerugian voucher > 80% dari budget campaign (over-budget) |
| `--meter-track` | `#E4E4E7` | Jalur rel background progress bar meter |

---

## 3. Typography System (Sistem Tipografi)

### 3.1 Font Families

```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
--font-mono: 'JetBrains Mono', 'SF Mono', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
```

---

### 3.2 Typographic Scale & Modular Tokens

| Token | Mobile Size | Desktop Size | Line Height | Weight | Tracking | Penggunaan |
|---|---|---|---|---|---|---|
| `--text-xs` | `11px` | `11px` | `14px` | `600` | `+0.05em` | Overline label (uppercase), status badge text |
| `--text-sm` | `13px` | `13px` | `18px` | `400` / `500` | `0` | Table cells, secondary caption, tab label, toast |
| `--text-base` | `14px` (input 16px) | `14px` | `20px` | `400` / `500` | `0` | Body text, card description, default text |
| `--text-md` | `15px` | `15px` | `22px` | `500` / `600` | `-0.01em` | Primary button label, subheadings |
| `--text-lg` | `17px` | `18px` | `24px` | `600` | `-0.01em` | Section heading, modal title, card title |
| `--text-xl` | `20px` | `24px` | `28px` | `600` | `-0.02em` | Page main title (Marketplace Monitor) |
| `--text-num` | `13px` | `13px` | `18px` | `500` | `0` | Angka data tabel, SKU ID, harga jual, margin (`--font-mono`) |
| `--text-num-lg`| `24px` | `28px` | `32px` | `700` | `-0.02em` | Angka besar Budget Meter (`--font-mono`) |

*Aturan Input Form Mobile*: Elemen `<input class="input-control">` menggunakan ukuran font fisik minimal `16px` pada viewport `< 640px` untuk menonaktifkan zoom otomatis browser seluler, dan kembali ke `14px` pada desktop.

---

## 4. Spacing, Radius & Elevation System

### 4.1 Spacing Scale (8-Point Grid)

| Token | Value | Penggunaan Tipikal |
|---|---|---|
| `--space-1` | `4px` | Micro spacing: jarak icon ke teks, vertical padding badge status |
| `--space-2` | `8px` | Tight gap: horizontal padding badge, jarak antar-tombol, dot margin |
| `--space-3` | `12px` | Compact gap: jarak header card ke isi, gap grid upload pada tablet |
| `--space-4` | `16px` | **Mobile Baseline**: Padding container mobile, padding kartu mobile |
| `--space-5` | `20px` | Medium gap: Padding kartu desktop, jarak antar-seksi pada mobile |
| `--space-6` | `24px` | **Desktop Baseline**: Padding container desktop, jarak antar-seksi desktop |
| `--space-8` | `32px` | Large layout gap: pemisah antar-grup informasi utama |
| `--space-10` | `40px` | Extra large gap: jarak display hero |

---

### 4.2 Border Radius

| Token | Value | Penerapan Komponen |
|---|---|---|
| `--radius-sm` | `4px` | Badge status kecil, tag marketplace, chip indikator |
| `--radius-md` | `6px` | Card utama, tombol primary/secondary, form input, toast pill |
| `--radius-lg` | `8px` | Upload dropzone box, container master data drawer |
| `--radius-full`| `9999px`| Status dot 6px, badge pill bulat, budget progress bar fill & track |

*Batasan Ketat*: Dilarang menggunakan border-radius lebih dari `8px` kecuali untuk elemen dengan token `--radius-full`.

---

### 4.3 Elevation & Shadows

| Token | Value | Penggunaan |
|---|---|---|
| `--shadow-sm` | `0 1px 2px rgba(0, 0, 0, 0.05)` | Elevasi default seluruh Card dan Box permukaan |
| `--shadow-md` | `0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.04)` | Hover card, elevated Toast notification |
| `--shadow-focus`| `0 0 0 2px var(--blue-500)` | Focus ring aksesibilitas keyboard/touch pada tombol & input |

*Prinsip Elevasi*: Jangan gunakan border tebal untuk membuat kontras elevasi. Gunakan garis tepi tipis `1px solid var(--gray-200)` dikombinasikan dengan `--shadow-sm`.

---

## 5. Komponen Antarmuka (Mobile-First Component Specs)

Setiap komponen di bawah ini dirancang dengan baseline mobile, kemudian dilengkapi dengan penyesuaian responsif untuk tablet dan desktop.

---

### 5.1 Header Bar

Navigasi atas statis yang menyediakan identitas aplikasi dan ringkasan kampanye aktif.

```
Baseline (Mobile < 640px):
  Position:       sticky top 0, z-index 100
  Height:         52px (memberikan ruang sentuh dan tampilan proporsional)
  Background:     var(--gray-900)
  Color:          var(--white)
  Padding:        0 var(--space-4)
  Display:        flex, align-items: center, justify-content: space-between
  Border-bottom:  none

  Kiri:           "SIRCLO Marketplace Monitor" (font: var(--text-base), weight: 600, color: var(--white))
  Kanan:          Ringkasan meta (font: var(--text-xs), color: rgba(255,255,255,0.7), text-align: right)
                  Teks: "10.10 Sale | Rp 5.000.000"

Desktop Enhancement (min-width: 768px):
  Height:         48px
  Padding:        0 var(--space-6)
  Kiri:           font: var(--text-base), weight: 600
  Kanan:          font: var(--text-sm), teks penuh: "10.10 Midnight Mega Sale | Budget Rp 5.000.000"
```

---

### 5.2 Master Data / COGS Management Section

Panel untuk mengelola data HPP agar tidak mengganggu fokus visual operator saat proses analisis.

```
Container:
  Background:     var(--white)
  Border:         1px solid var(--gray-200)
  Border-radius:  var(--radius-md)
  Padding:        var(--space-3) var(--space-4)
  Box-shadow:     var(--shadow-sm)
  Display:        flex, flex-direction: column, gap: var(--space-2)

Header Row:
  Display:        flex, justify-content: space-between, align-items: center
  Kiri:           Overline "Master Data" + Subtitle "Data COGS / HPP"
  Kanan:          Badge neutral (misal: "50 SKU Terdaftar") + Tombol Secondary "Kelola HPP"

Interaktivitas:
  Tombol "Kelola HPP" membuka/menutup drawer upload file HPP (collapsible) secara dinamis
  agar tidak memakan tempat di layar sempit ponsel.
```

---

### 5.3 Budget Meter KPI Card

Kartu indikator risiko finansial yang memantau total kerugian voucher vs alokasi budget kampanye.

```
Container:
  Background:     var(--white)
  Border:         1px solid var(--gray-200)
  Border-radius:  var(--radius-md)
  Padding:        var(--space-4) (Mobile) -> var(--space-5) (Desktop)
  Box-shadow:     var(--shadow-sm)

Header Row:
  Display:        flex, justify-content: space-between, align-items: center
  Label Kiri:     var(--text-xs), uppercase, letter-spacing 0.05em, color var(--gray-500)
                  Teks: "BUDGET CAMPAIGN"
  Badge Kanan:    Status badge (Aman / Perhatian / Kritis)

Nilai Utama (Hero Figure):
  Font:           var(--text-num-lg), font-mono, tabular-nums
  Color:          Warna meter aktif (--meter-safe / --meter-caution / --meter-over)
  Format Teks:    "Rp 3.250.000 / Rp 5.000.000"
  Margin-top:     var(--space-1)

Sub-teks:
  Font:           var(--text-sm), color var(--gray-500)
  Teks:           "65% terpakai"
  Margin-top:     var(--space-1)

Progress Bar Track:
  Margin-top:     var(--space-3)
  Height:         8px (Mobile, touch-friendly) -> 6px (Desktop)
  Border-radius:  var(--radius-full)
  Background:     var(--meter-track)
  Overflow:       hidden

Progress Bar Fill:
  Height:         100%
  Border-radius:  var(--radius-full)
  Background:     Warna meter aktif
  Transition:     width 0.4s ease
```

---

### 5.4 Upload Area & Dropzone Slots

Empat slot upload file data tabular (mendukung CSV, Excel seperti `.xlsx` / `.xls`, dan TSV) untuk Shopee Orders, TikTok Orders, Shopee Stok, dan TikTok Stok.

```
Grid Layout:
  Mobile (< 640px):       1 kolom (stacked vertical), gap: var(--space-3)
  Tablet/Desktop (>=640px): 2 kolom (2x2 grid), gap: var(--space-3)

Upload Slot Box:
  Min-height:     72px (memenuhi target sentuhan mobile)
  Padding:        var(--space-4)
  Border:         1px dashed var(--gray-300)
  Border-radius:  var(--radius-lg)
  Background:     var(--white)
  Display:        flex, flex-direction: column, align-items: center, justify-content: center
  Cursor:         pointer
  Text-align:     center
  Transition:     border-color 0.15s ease, background-color 0.15s ease

Teks Slot:
  Label:          var(--text-xs), weight 600, uppercase, letter-spacing 0.05em, color var(--gray-600)
  Hint:           var(--text-sm), color var(--gray-400), margin-top: 2px (e.g. "Pilih atau drop file CSV / Excel")

States:
  Hover:          border-color: var(--gray-400)
  Drag-over:      border-color: var(--blue-500), background-color: var(--blue-50)
  Filled:         border: 1px solid var(--blue-500), background-color: var(--blue-50)
                  Label tetap tampil, hint digantikan nama file terpilih (var(--text-sm), weight 500, color var(--gray-800))
  Focus-visible:  box-shadow: var(--shadow-focus)
```

---

### 5.5 Campaign Action Bar & Form Controls (Penerapan 1 Action Per Page)

Area kontrol budget dan pemicu analisis utama.

```
Layout:
  Mobile (< 640px):
    Flex-direction: column (stacked), gap: var(--space-2)
    Input control:  Lebar 100%
    Tombol Primary: Lebar 100% (Urutan teratas aksi: Grade 1 Primary CTA)
    Tombol Sample:  Lebar 100% (Opsi bantuan: Grade 2 Secondary CTA)

  Desktop (>= 640px):
    Flex-direction: row, align-items: center, gap: var(--space-3)
    Input budget di sisi kiri
    Tombol Primary dan Secondary berjajar di kanan

Input Control (Budget):
  Display:        flex, align-items: center
  Border:         1px solid var(--gray-300)
  Border-radius:  var(--radius-md)
  Background:     var(--white)
  Height:         44px (touch target compliant)
  Prefix label:   var(--text-sm), color var(--gray-500), padding-left var(--space-3)
  Field input:    border none, outline none, font-mono, tabular-nums, padding 0 var(--space-3)
  Focus-within:   border-color var(--blue-500), box-shadow var(--shadow-focus)

Tombol Primary — "Analisis Sekarang" (Grade 1 Primary CTA):
  Background:     var(--blue-500)
  Color:          var(--white)
  Font:           var(--text-md), weight 600
  Height:         44px (min-height standar mobile)
  Padding:        0 var(--space-5)
  Border:         none
  Border-radius:  var(--radius-md)
  Cursor:         pointer
  Display:        inline-flex, align-items: center, justify-content: center
  Transition:     background-color 0.15s ease, transform 0.1s ease

  Hover:          background var(--blue-600)
  Active:         transform scale(0.98)
  Disabled:       opacity 0.4, pointer-events none
  Focus-visible:  box-shadow var(--shadow-focus), outline none

Tombol Secondary — "Muat Data Sample 10.10" (Grade 2 Secondary Action):
  Background:     var(--white)
  Border:         1px solid var(--gray-200)
  Color:          var(--gray-700)
  Font:           var(--text-sm), weight 500
  Height:         44px
  Padding:        0 var(--space-4)
  Border-radius:  var(--radius-md)
  Cursor:         pointer
  Transition:     all 0.15s ease

  Hover:          background var(--gray-50), border-color var(--gray-300)
  Active:         transform scale(0.98)
```

---

### 5.6 Tab Navigation

Menu tab untuk berpindah antara tiga kategori hasil analisis: Jual Rugi, Prediksi Habis, dan Rebalancing.

```
Container:
  Display:        flex
  Border-bottom:  1px solid var(--gray-200)
  Margin-bottom:  var(--space-4)
  Overflow-x:     auto (Mobile: swipe horizontal tanpa wrap)
  Scrollbar:      none (-webkit-overflow-scrolling: touch)
  Gap:            var(--space-1)

Tab Item Button:
  Min-height:     44px (target sentuhan jari yang nyaman)
  Padding:        0 var(--space-4)
  Font:           var(--text-sm), weight 400
  Color:          var(--gray-500)
  Background:     transparent
  Border:         none
  Border-bottom:  2px solid transparent
  Cursor:         pointer
  White-space:    nowrap
  Display:        inline-flex, align-items: center, gap: var(--space-2)
  Transition:     color 0.15s ease, border-color 0.15s ease

Tab Item Hover:
  Color:          var(--gray-800)

Tab Item Active:
  Color:          var(--gray-900)
  Font-weight:    600
  Border-bottom:  2px solid var(--gray-900)

Count Badge di Dalam Tab:
  Font:           var(--text-xs), weight 600, font-mono
  Padding:        2px 6px
  Border-radius:  var(--radius-sm)
  Background:     var(--gray-100)
  Color:          var(--gray-600)
  Active Tab:     Background var(--gray-200), color var(--gray-900)
```

---

### 5.7 Alert Card (Jual Rugi & Rebalancing)

Komponen kartu individual untuk menampilkan produk berisiko. Seluruh area kartu dapat disentuh/diklik untuk langsung menyalin rekomendasi tindakan ke clipboard.

```
Container:
  Background:     var(--white)
  Border:         1px solid var(--gray-200)
  Border-left:    3px solid var(--status-{level}-dot)
  Border-radius:  var(--radius-md)
  Padding:        var(--space-4)
  Margin-bottom:  var(--space-2)
  Box-shadow:     var(--shadow-sm)
  Cursor:         pointer
  Display:        flex, flex-direction: column, gap: var(--space-2)
  Transition:     box-shadow 0.15s ease, transform 0.1s ease

Hover / Touch:
  Hover:          box-shadow: var(--shadow-md)
  Active/Tap:     transform: scale(0.99)

Layout Struktur Kartu:
  Baris 1 (Header):
    Display:      flex, justify-content: space-between, align-items: center
    Kiri:         [Dot 6px] + OVERLINE STATUS (font: var(--text-xs), uppercase, weight 600)
    Kanan:        Marketplace Tag ("Shopee" / "TikTok", font: var(--text-xs), background: var(--gray-100))

  Baris 2 (Identitas Produk):
    Teks:         SKU + Nama Produk (font: var(--text-base), weight 500, color: var(--gray-800))
    Word-break:   break-word

  Baris 3 (Metrik Finansial / Stok):
    Display:      grid, grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)), gap: var(--space-2)
    Angka:        font: var(--text-num), font-mono, tabular-nums
    Label metrik: font: var(--text-xs), color: var(--gray-500)
    Nilai rugi:   font: var(--text-num), weight 600, color: var(--status-negative-text)

Umpan Balik Ketukan (Tap Action):
  Saat kartu disentuh/diklik:
  - Teks aksi disalin otomatis ke clipboard pengguna.
  - Toast notifikasi "Pesan aksi disalin" muncul selama 3 detik.
```

---

### 5.8 Responsive Data Table (Prediksi Habis)

Tabel run rate 7 kolom (`SKU`, `Channel`, `Terjual`, `Run Rate/Jam`, `Stok`, `Prediksi Habis`, `Status`) yang dioptimalkan untuk mobile.

```
Wrapper (.table-wrapper):
  Width:          100%
  Border:         1px solid var(--gray-200)
  Border-radius:  var(--radius-md)
  Overflow-x:     auto
  -webkit-overflow-scrolling: touch
  Background:     var(--white)

Table Structure:
  Width:          100%
  Border-collapse: collapse
  Min-width:      600px (memastikan data tidak terhimpit di layar sempit)

Table Header (th):
  Background:     var(--gray-50)
  Font:           var(--text-xs), uppercase, letter-spacing 0.05em, weight 600
  Color:          var(--gray-500)
  Padding:        var(--space-2) var(--space-3)
  Text-align:     left
  Border-bottom:  1px solid var(--gray-200)
  White-space:    nowrap

Table Cell (td):
  Padding:        var(--space-3)
  Font:           var(--text-sm), color: var(--gray-700)
  Border-bottom:  1px solid var(--gray-100)
  Vertical-align: middle

Cell Angka / Finansial (td.num):
  Font:           var(--text-num), font-mono, tabular-nums
  Text-align:     right

Baris Hover:
  Background:     var(--gray-50)

Baris Terakhir:
  Border-bottom:  none
```

---

### 5.9 Toast Notification Component

Notifikasi umpan balik sementara yang muncul setelah pengguna menyalin teks atau berhasil memproses data.

```
Penempatan Mobile-First:
  Mobile (< 768px):
    Position:     fixed
    Bottom:       calc(var(--space-4) + env(safe-area-inset-bottom))
    Left:         var(--space-4)
    Right:        var(--space-4)
    Width:        auto
    Max-width:    none
    Text-align:   center

  Desktop (>= 768px):
    Bottom:       24px
    Right:        24px
    Left:         auto
    Max-width:    320px
    Text-align:   left

Visual:
  Background:     var(--gray-900)
  Color:          var(--white)
  Font:           var(--text-sm), weight 500
  Padding:        var(--space-3) var(--space-4)
  Border-radius:  var(--radius-md)
  Box-shadow:     var(--shadow-md)
  Z-index:        1000

Animasi:
  Opacity:        0 -> 1 (transisi 0.2s ease)
  Transform:      translateY(10px) -> translateY(0)
  Auto-dismiss:   Menghilang otomatis setelah 3 detik
```

---

### 5.10 Action Footer & Tombol "Salin Ringkasan"

Aksi final setelah proses analisis selesai untuk menyebarkan ringkasan lengkap ke grup WhatsApp.

```
Container:
  Display:        flex
  Margin-top:     var(--space-4)

  Mobile (< 640px):
    Width:        100%
    Button width: 100% (Full-width button)

  Desktop (>= 640px):
    Justify-content: flex-end
    Button width: auto

Tombol "Salin Ringkasan":
  Background:     var(--white)
  Border:         1px solid var(--gray-300)
  Color:          var(--gray-700)
  Font:           var(--text-sm), weight 600
  Height:         44px
  Padding:        0 var(--space-5)
  Border-radius:  var(--radius-md)
  Cursor:         pointer
  Display:        inline-flex, align-items: center, justify-content: center
  Transition:     all 0.15s ease

  Hover:          background var(--gray-50), border-color var(--gray-400), color var(--gray-900)
  Active:         transform scale(0.98)
```

---

### 5.11 Status Badges & Dot Indicators

```
Dot:
  Width:          6px
  Height:         6px
  Border-radius:  var(--radius-full)
  Display:        inline-block
  Margin-right:   var(--space-2)
  Background:     var(--status-{level}-dot)

Badge Pill:
  Display:        inline-flex
  Align-items:    center
  Padding:        2px 8px
  Border-radius:  var(--radius-sm)
  Font:           var(--text-xs), weight 600
  Text-transform: uppercase
  Letter-spacing: 0.05em
  Background:     var(--status-{level}-bg)
  Color:          var(--status-{level}-text)
```

---

## 6. Page Layout & Breakpoint System

### 6.1 Breakpoint Spectrum

Sistem breakpoint menggunakan pendekatan mobile-first progresif:

| Breakpoint | Lebar Layar | Target Perangkat | Karakter Layout |
|---|---|---|---|
| **Mobile (Base)** | `< 640px` | Smartphone (iPhone, Android) | 1 Kolom penuh, padding 16px, tombol 100% width, tabel horizontal scroll |
| **Tablet** | `640px – 1023px` | iPad, tablet, phablet lanskap | Grid upload 2 kolom, form budget inline, padding 20px |
| **Desktop** | `>= 1024px` | Laptop, desktop monitor | Maksimal 960px centered, padding 24px, toast bottom-right |

---

### 6.2 Page Container Specs

```css
/* Baseline Mobile */
.page-container {
  width: 100%;
  margin: 0 auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Tablet Enhancement */
@media (min-width: 640px) {
  .page-container {
    padding: var(--space-5);
    gap: var(--space-5);
  }
}

/* Desktop Enhancement */
@media (min-width: 1024px) {
  .page-container {
    max-width: 960px;
    padding: var(--space-6);
  }
}
```

---

### 6.3 Urutan Vertikal Hirarki Visual (1-Flow Journey)

Halaman ditata secara linear mengikuti alur kerja operator (*Input -> Trigger -> Action*):

1. **Header Bar**: Identitas aplikasi & ringkasan limit campaign (Full-width, Sticky Top).
2. **Master Data Banner**: Status HPP aktif & tombol drawer Kelola HPP.
3. **Budget Meter KPI Card**: Gambaran status risiko keuangan instan (Aman / Kuning / Merah).
4. **Upload Grid**: 4 slot file marketplace (Shopee Orders, TikTok Orders, Shopee Stok, TikTok Stok).
5. **Campaign Action Bar**: Input budget + **Tombol Primary [Analisis Sekarang]** + Tombol Secondary [Muat Sample].
6. **Tab Navigation**: Tab filter Jual Rugi, Prediksi Habis, dan Rebalancing dilengkapi badge counter.
7. **Results Viewport**:
   - Tab Jual Rugi: Alert cards kartu merah/kuning dengan aksi salin otomatis.
   - Tab Prediksi Habis: Tabel data run rate monospaced dengan horizontal scroll.
   - Tab Rebalancing: Kartu rekomendasi transfer stok gudang ke marketplace.
8. **Final Dispatch Action**: Tombol **[Salin Ringkasan]** ke grup WhatsApp manajemen.
9. **Toast Notification Layer**: Notifikasi konfirmasi di bagian bawah layar.

---

## 7. Panduan State Antarmuka & UX Feedback

| State | Tampilan Antarmuka | Aksi Pengguna |
|---|---|---|
| **Empty State** | Slot upload bergaris putus-putus abu-abu (`--gray-300`). Area tab menampilkan pesan instruksi netral: *"Silakan upload 4 file marketplace (CSV atau Excel) atau klik 'Muat Data Sample 10.10' untuk memulai analisis."* | Upload file atau klik **[Muat Data Sample 10.10]**. |
| **Loading State** | Tombol **[Analisis Sekarang]** menampilkan status *"Menganalisis..."*, opacity 0.7, pointer-events dinonaktifkan. Indikator loading muncul jika proses > 2 detik. | Sistem memproses join SKU di background. |
| **Success State** | Budget meter terisi warna semantik, badge counter tab bertambah, Alert Cards berurutan dari yang paling kritis di atas (*descending severity*). | Meninjau produk rugi atau stok habis. |
| **Feedback State** | Mengetuk Alert Card atau tombol Salin Ringkasan memicu Toast *"Pesan aksi disalin"* / *"Ringkasan disalin ke clipboard"* selama 3 detik. | Paste teks ke grup WhatsApp tim operasional. |
| **Error State** | Pesan error spesifik muncul dengan background `--status-negative-bg` dan border `--status-negative-dot` (misal: *"Kolom 'sku_reference_no' tidak ditemukan di file Shopee Orders"* atau *"Format file tidak didukung. Harap upload CSV atau Excel (.xlsx/.xls)"*). | Pengguna memperbaiki file input. |

---

## 8. Aturan Ketat & Batasan Desain (Strict Quality Checklist)

Seluruh kontributor kode dan antarmuka WAJIB mematuhi daftar larangan berikut:

1. **Dilarang Menggunakan Emoji**:
   - Dilarang menyertakan karakter emoji Unicode di seluruh elemen antarmuka, HTML template, CSS content, pesan toast, dan kode sumber frontend.
   - Indikator status wajib menggunakan titik lingkaran 6px (`[dot 6px]` / `var(--radius-full)`) dan badge teks semantik.
2. **Dilarang Menggunakan Gradien**:
   - Seluruh latar belakang tombol, card, bar, dan halaman wajib menggunakan warna solid murni.
3. **Radius Maksimum 8px**:
   - Dilarang membuat `border-radius` lebih dari `8px` (`--radius-lg`), kecuali untuk bentuk bulat penuh seperti status dot dan pill progress bar (`--radius-full`).
4. **Hanya Dua Font Terdaftar**:
   - Dilarang mengimpor atau menggunakan font selain `Inter` (`--font-sans`) dan `JetBrains Mono` (`--font-mono`).
5. **Kepatuhan 1 Action Per Page**:
   - Dilarang menampilkan dua tombol Primary (berlatar belakang solid `--blue-500`) yang bersaing dalam satu layar.
   - Pada layar input, hanya tombol **[Analisis Sekarang]** yang menjadi Primary. Tombol lainnya wajib menggunakan gaya Secondary.
6. **Standar Touch Target Minimal 44px**:
   - Seluruh elemen interaktif pada perangkat bergerak wajib memiliki tinggi fisik minimal 44px atau area klik diperluas dengan padding minimal 44px.
7. **Penyelarasan Numerik Monospaced**:
   - Seluruh nominal Rupiah, ID SKU, stok unit, nilai run rate per jam, dan persentase wajib menggunakan `--font-mono` dan format numerik Indonesia standar (pemisah ribuan menggunakan titik).

# Panduan Perhitungan Analitik PLN dengan PZEM 004T

## 📋 Daftar Isi
1. [Cara Kerja PZEM 004T](#cara-kerja-pzem-004t)
2. [Struktur Tarif PLN](#struktur-tarif-pln)
3. [Perhitungan Energi di Sistem](#perhitungan-energi-di-sistem)
4. [Memastikan Akurasi Pengukuran](#memastikan-akurasi-pengukuran)
5. [Kalibrasi dan Validasi](#kalibrasi-dan-validasi)
6. [Troubleshooting Discrepancy](#troubleshooting-discrepancy)

---

## 🔌 Cara Kerja PZEM 004T

### Fitur PZEM 004T
PZEM 004T adalah modul monitoring energi listrik yang dapat mengukur:
- **Voltage (V)**: Tegangan listrik (AC)
- **Current (A)**: Arus listrik
- **Power (W)**: Daya aktif (Active Power)
- **Energy (kWh)**: Energi kumulatif (Energy Counter)
- **Frequency (Hz)**: Frekuensi (biasanya 50Hz di Indonesia)
- **Power Factor**: Faktor daya (0.0 - 1.0)

### Cara Kerja Energy Counter
PZEM 004T memiliki **energy counter** yang:
- **Akumulatif**: Nilai terus bertambah seiring waktu
- **Resetable**: Bisa di-reset ke 0 (biasanya saat restart atau reset manual)
- **Satuan**: kWh (kilowatt-hour)
- **Akurasi**: ±1% (tergantung kalibrasi)

**Contoh:**
```
Saat ini:  Energy = 1234.567 kWh
1 jam lalu: Energy = 1234.123 kWh
Konsumsi 1 jam = 1234.567 - 1234.123 = 0.444 kWh
```

### Data yang Dikirim ke Sistem
PZEM mengirim data via MQTT dalam format JSON:
```json
{
  "device_address": "PZEM_R",
  "voltage": 220.5,
  "current": 5.25,
  "power": 1157.6,
  "energy": 1234.567,
  "frequency": 50.0,
  "power_factor": 0.95
}
```

---

## 💰 Struktur Tarif PLN

### Golongan Tarif (2024)
PLN menggunakan **tarif blok** (block tariff) dengan beberapa golongan:

#### 1. R1 (Rumah Tangga)
- **Blok 1**: 0-900 kWh → Rp 1.352/kWh
- **Blok 2**: >900 kWh → Rp 1.445/kWh
- **Abonemen**: Rp 11.000/bulan (daya ≤ 2.200 VA)

#### 2. R2 (Rumah Tangga Daya Besar)
- **Blok 1**: 0-1.300 kWh → Rp 1.352/kWh
- **Blok 2**: >1.300 kWh → Rp 1.445/kWh
- **Abonemen**: Rp 20.000/bulan (daya > 2.200 VA)

#### 3. B2 (Bisnis)
- **Blok 1**: 0-200 kWh → Rp 1.445/kWh
- **Blok 2**: >200 kWh → Rp 1.699/kWh
- **Abonemen**: Rp 40.000/bulan

#### 4. I3 (Industri)
- **Tarif**: Rp 1.699/kWh (flat)
- **Abonemen**: Rp 40.000/bulan

### Perhitungan Tagihan PLN

#### Rumus Dasar
```
Total Tagihan = (Energi Blok 1 × Tarif Blok 1) + 
                (Energi Blok 2 × Tarif Blok 2) + 
                Abonemen + 
                Pajak (11% PPN)
```

#### Contoh Perhitungan R1 (Konsumsi 1.200 kWh)

**Step 1: Hitung Energi per Blok**
```
Total Konsumsi: 1.200 kWh
Blok 1: min(1.200, 900) = 900 kWh
Blok 2: max(0, 1.200 - 900) = 300 kWh
```

**Step 2: Hitung Biaya Energi**
```
Biaya Blok 1: 900 kWh × Rp 1.352 = Rp 1.216.800
Biaya Blok 2: 300 kWh × Rp 1.445 = Rp 433.500
Total Biaya Energi: Rp 1.650.300
```

**Step 3: Tambah Abonemen**
```
Subtotal: Rp 1.650.300 + Rp 11.000 = Rp 1.661.300
```

**Step 4: Tambah PPN 11%**
```
PPN: Rp 1.661.300 × 11% = Rp 182.743
Total Tagihan: Rp 1.661.300 + Rp 182.743 = Rp 1.844.043
```

#### Contoh Perhitungan R1 (Konsumsi 500 kWh)

**Step 1: Hitung Energi per Blok**
```
Total Konsumsi: 500 kWh
Blok 1: min(500, 900) = 500 kWh
Blok 2: max(0, 500 - 900) = 0 kWh
```

**Step 2: Hitung Biaya Energi**
```
Biaya Blok 1: 500 kWh × Rp 1.352 = Rp 676.000
Biaya Blok 2: 0 kWh × Rp 1.445 = Rp 0
Total Biaya Energi: Rp 676.000
```

**Step 3: Tambah Abonemen**
```
Subtotal: Rp 676.000 + Rp 11.000 = Rp 687.000
```

**Step 4: Tambah PPN 11%**
```
PPN: Rp 687.000 × 11% = Rp 75.570
Total Tagihan: Rp 687.000 + Rp 75.570 = Rp 762.570
```

### ⚠️ Catatan Penting

1. **Tarif Blok Bersifat Kumulatif**
   - Blok 1 dihitung dulu sampai batas maksimum
   - Sisa konsumsi masuk ke Blok 2
   - Tidak ada "tarif rata-rata"

2. **Abonemen Selalu Dikenakan**
   - Dibayar setiap bulan, terlepas dari konsumsi
   - Tidak dipengaruhi oleh jumlah kWh

3. **PPN Dihitung Setelah Abonemen**
   - PPN = 11% dari (Biaya Energi + Abonemen)
   - Bukan 11% dari biaya energi saja

### Periode Billing PLN
- **Periode**: 1 bulan kalender (biasanya tanggal 1-30/31)
- **Pembacaan**: Meteran dibaca setiap bulan
- **Selisih**: Bisa terjadi karena:
  - Perbedaan tanggal billing
  - Losses di jaringan
  - Kalibrasi meteran

---

## ⚡ Perhitungan Energi di Sistem

### Metode 1: Energy Counter Difference (Paling Akurat)
**Prioritas tertinggi** jika energy counter valid.

```sql
Energy Consumed = MAX(energy) - MIN(energy)
```

**Contoh:**
```
Start: 2024-11-01 00:00:00, Energy = 1000.000 kWh
End:   2024-11-30 23:59:59, Energy = 1200.500 kWh
Konsumsi = 1200.500 - 1000.000 = 200.500 kWh
```

**Validasi:**
- ✅ `MAX(energy) >= MIN(energy)` (tidak boleh negatif)
- ✅ `(MAX - MIN) < 10000 kWh` (sanity check)
- ✅ `COUNT(*) > 1` (minimal 2 data point)

### Metode 2: Trapezoidal Integration (Fallback)
Jika energy counter tidak valid, hitung dari power dengan **trapezoidal integration**.

```sql
Energy = Σ [(Power(t) + Power(t-1)) / 2 × Δt]
```

**Rumus:**
```
Energy (kWh) = Σ [(P(t) + P(t-1)) / 2 × (t - t-1) / 3600 / 1000]
```

**Contoh:**
```
t0: Power = 1000W, Time = 10:00:00
t1: Power = 1200W, Time = 10:01:00 (60 detik = 1/3600 jam)

Energy = (1000 + 1200) / 2 × (60 / 3600) / 1000
       = 1100 × 0.0002778
       = 0.3056 kWh
```

### Metode 3: Average Power × Duration (Fallback Terakhir)
Jika kedua metode di atas gagal:

```sql
Energy = AVG(power) × (MAX(created_at) - MIN(created_at)) / 3600 / 1000
```

**Contoh:**
```
Avg Power = 1100W
Duration = 720 jam (30 hari)
Energy = 1100 × 720 / 3600 / 1000 = 0.22 kWh
```

### Implementasi di Sistem
File: `dashboard/report_generator.py` (lines 247-316)

```python
CASE 
    -- Method 1: Energy counter (most accurate)
    WHEN MAX(p.energy) IS NOT NULL 
         AND MAX(p.energy) >= MIN(p.energy)
         AND (MAX(p.energy) - MIN(p.energy)) < 10000
         AND COUNT(*) > 1
    THEN MAX(p.energy) - MIN(p.energy)
    
    -- Method 2: Trapezoidal integration
    WHEN ec.energy_from_power IS NOT NULL 
    THEN ec.energy_from_power
    
    -- Method 3: Average power × duration
    ELSE AVG(p.power) × DURATION / 3600 / 1000
END
```

---

## 🎯 Memastikan Akurasi Pengukuran

### 1. Pemasangan Sensor yang Benar

#### PZEM 004T untuk 1 Phase
```
L (Line) → Masuk ke PZEM
N (Neutral) → Masuk ke PZEM
CT (Current Transformer) → Mengelilingi kabel L
```

#### PZEM 004T untuk 3 Phase
```
Phase R → PZEM_R (device_address: "PZEM_R")
Phase S → PZEM_S (device_address: "PZEM_S")
Phase T → PZEM_T (device_address: "PZEM_T")
```

**Total 3 Phase:**
```
Total Energy = Energy_R + Energy_S + Energy_T
```

### 2. Kalibrasi Energy Counter

#### Reset Energy Counter
Jika perlu reset (misal setelah maintenance):
```python
# Di firmware ESP32/Arduino
pzem.resetEnergy();
```

**⚠️ PENTING:** Setelah reset, pastikan:
- Database mencatat nilai energy sebelum reset
- Sistem menggunakan metode fallback (trapezoidal) selama transisi
- Dokumentasikan waktu reset untuk perhitungan manual

### 3. Sampling Rate yang Cukup

**Rekomendasi:**
- **Minimum**: 1 data per menit (60 detik)
- **Optimal**: 1 data per 30 detik
- **Maksimum**: 1 data per 5 detik (untuk monitoring real-time)

**Alasan:**
- Sampling terlalu jarang → kehilangan detail fluktuasi
- Sampling terlalu sering → beban database tinggi

**Konfigurasi di ESP32:**
```cpp
#define SAMPLE_INTERVAL 60  // detik
```

### 4. Sinkronisasi Waktu

**PENTING:** Pastikan semua device menggunakan waktu yang sama!

**Solusi:**
- Gunakan **NTP (Network Time Protocol)**
- Set timezone ke `Asia/Jakarta`
- Sinkronkan setiap 24 jam

**Contoh (ESP32):**
```cpp
configTime(7 * 3600, 0, "pool.ntp.org");  // GMT+7 (WIB)
```

### 5. Validasi Data

**Checks yang dilakukan sistem:**
- ✅ Voltage: 180V - 250V (normal untuk Indonesia)
- ✅ Current: > 0 (tidak boleh negatif)
- ✅ Power: Voltage × Current × Power Factor (validasi)
- ✅ Energy: Monotonik naik (tidak boleh turun kecuali reset)
- ✅ Frequency: 49.5Hz - 50.5Hz

---

## 🔍 Kalibrasi dan Validasi

### Step 1: Bandingkan dengan Meteran PLN

**Langkah:**
1. Catat **meteran PLN** pada tanggal tertentu (misal: 1 Nov 2024)
2. Catat **energy counter PZEM** pada waktu yang sama
3. Setelah 1 bulan, catat lagi kedua nilai
4. Bandingkan selisihnya

**Contoh:**
```
Tanggal 1 Nov 2024:
- Meteran PLN: 5000.000 kWh
- PZEM Counter: 1000.000 kWh
- Offset: 4000.000 kWh

Tanggal 1 Des 2024:
- Meteran PLN: 5200.000 kWh
- PZEM Counter: 1200.000 kWh
- Offset: 4000.000 kWh (harus sama!)

Konsumsi PLN: 5200 - 5000 = 200 kWh
Konsumsi PZEM: 1200 - 1000 = 200 kWh
✅ Match!
```

### Step 2: Hitung Error Percentage

```
Error % = |(PZEM - PLN) / PLN| × 100%
```

**Target:**
- **Excellent**: < 1%
- **Good**: < 3%
- **Acceptable**: < 5%
- **Needs Calibration**: > 5%

### Step 3: Kalibrasi jika Perlu

**Jika error > 5%:**

1. **Cek CT Ratio**
   - Pastikan CT ratio sesuai dengan rating
   - Contoh: CT 100A/5A → ratio = 20

2. **Cek Voltage Calibration**
   - Ukur dengan multimeter
   - Bandingkan dengan PZEM reading
   - Adjust jika perlu

3. **Cek Power Factor**
   - Pastikan power factor dihitung dengan benar
   - Gunakan power meter referensi

### Step 4: Validasi dengan Load Test

**Test dengan beban diketahui:**
```
Load: 1000W (1 kW)
Duration: 1 jam
Expected Energy: 1.000 kWh

Actual Energy (PZEM): ?
Error: ?
```

---

## 🐛 Troubleshooting Discrepancy

### Masalah 1: PZEM Lebih Besar dari PLN

**Kemungkinan Penyebab:**
1. **Losses tidak terhitung**: PLN meteran di upstream, PZEM di downstream
   - **Solusi**: Normal, karena ada losses di kabel/jaringan
   
2. **Multiple PZEM**: Mengukur beberapa beban terpisah
   - **Solusi**: Pastikan semua PZEM dihitung
   
3. **Kalibrasi salah**: CT ratio atau voltage calibration
   - **Solusi**: Re-calibrate

### Masalah 2: PZEM Lebih Kecil dari PLN

**Kemungkinan Penyebab:**
1. **Beban tidak terukur**: Ada beban yang tidak melalui PZEM
   - **Solusi**: Pastikan semua beban terukur
   
2. **Energy counter reset**: Terjadi reset di tengah periode
   - **Solusi**: Gunakan metode fallback (trapezoidal)
   
3. **Data loss**: Data tidak tersimpan ke database
   - **Solusi**: Cek log MQTT, pastikan tidak ada gap

### Masalah 3: Fluktuatif (Kadang Lebih, Kadang Kurang)

**Kemungkinan Penyebab:**
1. **Sampling rate terlalu rendah**: Kehilangan detail
   - **Solusi**: Kurangi interval sampling (30 detik)
   
2. **Time sync issue**: Timestamp tidak akurat
   - **Solusi**: Pastikan NTP sync bekerja
   
3. **Power factor tidak akurat**: Menyebabkan perhitungan salah
   - **Solusi**: Validasi power factor dengan meteran referensi

---

## 📊 Best Practices

### 1. Monitoring Harian
- **Cek energy counter** setiap hari
- **Bandingkan dengan estimasi** berdasarkan power rata-rata
- **Alert jika ada anomaly** (energy turun, power negatif, dll)

### 2. Backup Data
- **Backup database** setiap hari
- **Simpan laporan bulanan** untuk referensi
- **Dokumentasikan reset/calibration**

### 3. Reporting
- **Generate report bulanan** untuk bandingkan dengan tagihan PLN
- **Include breakdown per phase** (untuk 3 phase)
- **Show trend** (konsumsi naik/turun)

### 4. Maintenance
- **Cek sensor** setiap 3 bulan
- **Validasi dengan meteran referensi** setiap 6 bulan
- **Update firmware** jika ada bug fix

---

## 🔧 Konfigurasi Sistem

### Environment Variables
File: `docker-compose.yml`

```yaml
environment:
  - ENERGY_TARIFF=1500  # Tarif per kWh (default)
  - TARIFF_BLOCK1=1352  # Tarif blok 1 (R1)
  - TARIFF_BLOCK2=1445  # Tarif blok 2 (R1)
  - TARIFF_THRESHOLD=900  # Threshold blok 1 (kWh)
  - ABONEMEN=11000  # Abonemen bulanan
```

### Custom Tarif di Report
File: `dashboard/report_generator.py` (lines 128-158)

```python
# Get tariff from environment
tariff_per_kwh = float(os.getenv('ENERGY_TARIFF', 1500))

# Calculate cost
total_cost = total_energy_kwh * tariff_per_kwh
```

**Untuk tarif blok:**
```python
if total_energy_kwh <= 900:
    cost = total_energy_kwh * 1352  # Blok 1
else:
    cost = (900 * 1352) + ((total_energy_kwh - 900) * 1445)  # Blok 2
cost += 11000  # Abonemen
cost *= 1.11  # PPN 11%
```

---

## 📈 Contoh Perhitungan Lengkap

### Skenario: Rumah Tangga (R1), Konsumsi 1.200 kWh/bulan

**Data PZEM:**
```
Tanggal 1 Nov: Energy = 5000.000 kWh
Tanggal 1 Des: Energy = 6200.000 kWh
Konsumsi = 1200.000 kWh
```

**Perhitungan Tagihan:**
```
Blok 1: 900 kWh × Rp 1.352 = Rp 1.216.800
Blok 2: 300 kWh × Rp 1.445 = Rp 433.500
Abonemen: Rp 11.000
Subtotal: Rp 1.661.300
PPN 11%: Rp 182.743
Total: Rp 1.844.043
```

**Validasi:**
```
Error vs Meteran PLN: < 1% ✅
Matching dengan tagihan: ✅
```

---

## 🎯 Panduan Praktis: Memastikan Matching dengan Tagihan PLN

### Step-by-Step Validasi Bulanan

#### 1. Catat Data Awal Bulan (Tanggal Billing PLN)

**Contoh: Tanggal 1 November 2024**
```
┌─────────────────────────────────────┐
│ Meteran PLN (di rumah):             │
│ 5000.000 kWh                        │
│                                     │
│ PZEM Energy Counter:                │
│ - PZEM_R: 1000.000 kWh              │
│ - PZEM_S: 1000.000 kWh              │
│ - PZEM_T: 1000.000 kWh              │
│ Total: 3000.000 kWh                 │
│                                     │
│ Offset (PLN - PZEM):               │
│ 5000.000 - 3000.000 = 2000.000 kWh │
└─────────────────────────────────────┘
```

**⚠️ PENTING:** Offset harus konsisten setiap bulan!

#### 2. Catat Data Akhir Bulan (Tanggal Billing PLN)

**Contoh: Tanggal 1 Desember 2024**
```
┌─────────────────────────────────────┐
│ Meteran PLN (di rumah):             │
│ 6200.000 kWh                        │
│                                     │
│ PZEM Energy Counter:                │
│ - PZEM_R: 1200.000 kWh              │
│ - PZEM_S: 1200.000 kWh              │
│ - PZEM_T: 1200.000 kWh              │
│ Total: 3600.000 kWh                 │
│                                     │
│ Offset (PLN - PZEM):               │
│ 6200.000 - 3600.000 = 2000.000 kWh │
│ ✅ Offset sama dengan awal bulan!   │
└─────────────────────────────────────┘
```

#### 3. Hitung Konsumsi

**Konsumsi PLN:**
```
6200.000 - 5000.000 = 1200.000 kWh
```

**Konsumsi PZEM:**
```
3600.000 - 3000.000 = 600.000 kWh (per phase)
Total 3 Phase: 600.000 × 3 = 1800.000 kWh ❌
```

**⚠️ MASALAH:** PZEM menunjukkan 1800 kWh, tapi PLN hanya 1200 kWh!

#### 4. Analisis Discrepancy

**Kemungkinan Penyebab:**

1. **PZEM mengukur di downstream, PLN di upstream**
   - Ada losses di kabel/jaringan
   - **Normal:** PZEM bisa 2-5% lebih besar

2. **Ada beban yang tidak terukur oleh PZEM**
   - Beban langsung dari panel utama
   - **Solusi:** Pastikan semua beban melalui PZEM

3. **Energy counter reset di tengah bulan**
   - **Solusi:** Cek log, gunakan metode fallback

4. **Perhitungan salah (3 phase vs 1 phase)**
   - **Koreksi:** Untuk 3 phase, total = R + S + T (bukan ×3)
   - Jika R=S=T=600 kWh, total = 600 kWh (bukan 1800 kWh)

#### 5. Validasi dengan Tagihan PLN

**Dari Tagihan PLN:**
```
Konsumsi: 1200 kWh
Blok 1: 900 kWh × Rp 1.352 = Rp 1.216.800
Blok 2: 300 kWh × Rp 1.445 = Rp 433.500
Abonemen: Rp 11.000
Subtotal: Rp 1.661.300
PPN 11%: Rp 182.743
Total: Rp 1.844.043
```

**Dari Sistem PZEM (jika konsumsi = 1200 kWh):**
```
Blok 1: 900 kWh × Rp 1.352 = Rp 1.216.800
Blok 2: 300 kWh × Rp 1.445 = Rp 433.500
Abonemen: Rp 11.000
Subtotal: Rp 1.661.300
PPN 11%: Rp 182.743
Total: Rp 1.844.043
✅ Match!
```

### Faktor-Faktor yang Mempengaruhi Selisih

#### 1. Losses di Jaringan (2-5%)
```
PZEM (downstream) > PLN (upstream)
Selisih: 2-5% adalah normal
```

#### 2. Periode Billing Tidak Sama
```
PLN: 1 Nov 00:00 - 1 Des 00:00
PZEM: 1 Nov 08:00 - 1 Des 08:00 (selisih 8 jam)
Solusi: Pastikan timestamp sama
```

#### 3. Kalibrasi Meteran
```
Meteran PLN: ±2% akurasi
PZEM 004T: ±1% akurasi
Total error: ±3% (normal)
```

#### 4. Power Factor
```
Jika power factor < 1.0:
- PZEM mengukur active power (W)
- PLN mengukur apparent power (VA)
- Bisa ada selisih kecil
```

### Toleransi Error yang Diterima

| Error % | Status | Tindakan |
|---------|--------|----------|
| < 1% | Excellent | ✅ Tidak perlu tindakan |
| 1-3% | Good | ✅ Normal, monitor saja |
| 3-5% | Acceptable | ⚠️ Cek kalibrasi |
| > 5% | Needs Calibration | ❌ Perlu kalibrasi ulang |

### Checklist Validasi Bulanan

- [ ] Catat meteran PLN di tanggal billing
- [ ] Catat energy counter PZEM di waktu yang sama
- [ ] Hitung offset (harus konsisten)
- [ ] Generate report dari sistem
- [ ] Bandingkan konsumsi PZEM vs PLN
- [ ] Hitung error percentage
- [ ] Jika error > 5%, lakukan kalibrasi
- [ ] Dokumentasikan hasil validasi

---

## 📝 Checklist Akurasi

- [ ] PZEM terpasang dengan benar (CT ratio sesuai)
- [ ] Energy counter tidak pernah reset tanpa dokumentasi
- [ ] Sampling rate minimal 1 data per menit
- [ ] Time sync aktif (NTP)
- [ ] Validasi data otomatis aktif
- [ ] Bandingkan dengan meteran PLN setiap bulan
- [ ] Error percentage < 3%
- [ ] Dokumentasi maintenance tersimpan
- [ ] Report bulanan di-generate otomatis
- [ ] Alert system aktif untuk anomaly

---

## 🆘 Support

Jika masih ada discrepancy yang tidak bisa dijelaskan:
1. **Cek log MQTT**: Pastikan tidak ada data loss
2. **Cek database**: Pastikan tidak ada gap timestamp
3. **Cek sensor**: Validasi dengan meteran referensi
4. **Cek wiring**: Pastikan tidak ada beban yang tidak terukur

---

**Last Updated:** 2024-11-18
**Version:** 1.0


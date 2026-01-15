# Panduan Penggunaan Formula Perhitungan PLN di Reporting

## 📋 Overview

Sistem reporting telah terintegrasi dengan **PLN Tariff Calculator** untuk menghitung tagihan PLN secara akurat berdasarkan sistem tarif blok (block tariff).

## 🔧 Konfigurasi

### Environment Variables

Tambahkan environment variables berikut di `docker-compose.yml` atau `.env`:

```yaml
environment:
  # Golongan tarif PLN (R1, R2, B2, I3)
  - PLN_TARIFF_CLASS=R1
  
  # Persentase PPN (default: 11%)
  - PLN_PPN_PERCENT=0.11
```

### Golongan Tarif yang Tersedia

| Golongan | Deskripsi | Blok 1 | Blok 2 | Abonemen |
|----------|-----------|--------|--------|----------|
| **R1** | Rumah Tangga (≤ 2.200 VA) | 0-900 kWh @ Rp 1.352/kWh | >900 kWh @ Rp 1.445/kWh | Rp 11.000 |
| **R2** | Rumah Tangga (> 2.200 VA) | 0-1.300 kWh @ Rp 1.352/kWh | >1.300 kWh @ Rp 1.445/kWh | Rp 20.000 |
| **B2** | Bisnis | 0-200 kWh @ Rp 1.445/kWh | >200 kWh @ Rp 1.699/kWh | Rp 40.000 |
| **I3** | Industri | Flat @ Rp 1.699/kWh | - | Rp 40.000 |

## 💻 Penggunaan di Code

### 1. Menggunakan di Report Generator

```python
from report_generator import ThreePhaseCalculator

# Hitung tagihan PLN
total_energy_kwh = 1200.0  # dari perhitungan energi
pln_billing = ThreePhaseCalculator.calculate_pln_billing(
    total_energy_kwh=total_energy_kwh,
    tariff_class='R1',  # optional, default dari env
    ppn_percent=0.11     # optional, default 11%
)

# Hasil perhitungan
print(f"Total Tagihan: Rp {pln_billing['total_bill_idr']:,.0f}")
print(f"Breakdown: {pln_billing['breakdown']}")
```

### 2. Menggunakan PLN Calculator Langsung

```python
from pln_calculator import PLNTariffCalculator, calculate_pln_bill

# Method 1: Menggunakan class
calculator = PLNTariffCalculator(tariff_class='R1')
result = calculator.calculate_bill(energy_kwh=1200)

print(f"Blok 1: {result.block1_energy} kWh × Rp {result.block1_cost:,.0f}")
print(f"Blok 2: {result.block2_energy} kWh × Rp {result.block2_cost:,.0f}")
print(f"Total: Rp {result.total_bill:,.0f}")

# Method 2: Menggunakan fungsi helper
bill = calculate_pln_bill(energy_kwh=1200, tariff_class='R1')
print(f"Total: Rp {bill['total_bill_idr']:,.0f}")
```

### 3. Dari Environment Variables

```python
from pln_calculator import PLNTariffCalculator

# Otomatis membaca dari env PLN_TARIFF_CLASS dan PLN_PPN_PERCENT
calculator = PLNTariffCalculator.from_environment()
result = calculator.calculate_bill(energy_kwh=1200)
```

## 📊 Format Output

### Struktur Return Value

```python
{
    'energy_kwh': 1200.0,                    # Total konsumsi energi
    'block1_energy_kwh': 900.0,              # Energi di blok 1
    'block2_energy_kwh': 300.0,              # Energi di blok 2
    'block1_cost_idr': 1216800.0,            # Biaya blok 1
    'block2_cost_idr': 433500.0,             # Biaya blok 2
    'energy_cost_idr': 1650300.0,            # Total biaya energi
    'abonemen_idr': 11000.0,                 # Abonemen bulanan
    'subtotal_idr': 1661300.0,               # Subtotal (energi + abonemen)
    'ppn_percent': 11.0,                     # Persentase PPN
    'ppn_amount_idr': 182743.0,              # Jumlah PPN
    'total_bill_idr': 1844043.0,             # TOTAL TAGIHAN
    'tariff_class': 'R1',                    # Golongan tarif
    'breakdown': {                           # Detail breakdown
        'block1_energy_kwh': 900.0,
        'block2_energy_kwh': 300.0,
        'block1_cost_idr': 1216800.0,
        'block2_cost_idr': 433500.0,
        'energy_cost_idr': 1650300.0,
        'abonemen_idr': 11000.0,
        'subtotal_idr': 1661300.0,
        'ppn_percent': 11.0,
        'ppn_amount_idr': 182743.0,
        'total_bill_idr': 1844043.0
    }
}
```

## 📄 Contoh Perhitungan

### Contoh 1: R1, Konsumsi 1.200 kWh

```python
bill = calculate_pln_bill(energy_kwh=1200, tariff_class='R1')

# Breakdown:
# Blok 1: 900 kWh × Rp 1.352 = Rp 1.216.800
# Blok 2: 300 kWh × Rp 1.445 = Rp 433.500
# Biaya Energi: Rp 1.650.300
# Abonemen: Rp 11.000
# Subtotal: Rp 1.661.300
# PPN 11%: Rp 182.743
# TOTAL: Rp 1.844.043
```

### Contoh 2: R1, Konsumsi 500 kWh

```python
bill = calculate_pln_bill(energy_kwh=500, tariff_class='R1')

# Breakdown:
# Blok 1: 500 kWh × Rp 1.352 = Rp 676.000
# Blok 2: 0 kWh
# Biaya Energi: Rp 676.000
# Abonemen: Rp 11.000
# Subtotal: Rp 687.000
# PPN 11%: Rp 75.570
# TOTAL: Rp 762.570
```

### Contoh 3: B2, Konsumsi 500 kWh

```python
bill = calculate_pln_bill(energy_kwh=500, tariff_class='B2')

# Breakdown:
# Blok 1: 200 kWh × Rp 1.445 = Rp 289.000
# Blok 2: 300 kWh × Rp 1.699 = Rp 509.700
# Biaya Energi: Rp 798.700
# Abonemen: Rp 40.000
# Subtotal: Rp 838.700
# PPN 11%: Rp 92.257
# TOTAL: Rp 930.957
```

## 🎯 Integrasi di Report PDF

Sistem reporting otomatis menampilkan:

1. **Executive Summary**: Total tagihan PLN dengan breakdown
2. **PLN Billing Breakdown**: Detail perhitungan lengkap
   - Konsumsi per blok
   - Biaya per blok
   - Abonemen
   - PPN
   - Total tagihan

### Contoh Output di Report

```
PLN BILLING BREAKDOWN
─────────────────────────────────────────────────────
Item              Detail                          Amount
─────────────────────────────────────────────────────
Total Konsumsi   1200.000 kWh                     -
Blok 1           900.000 kWh × Rp 1.352/kWh       1.216.800
Blok 2           300.000 kWh × Rp 1.445/kWh       433.500
Biaya Energi     Blok 1 + Blok 2                 1.650.300
Abonemen         Golongan R1                      11.000
Subtotal         Biaya Energi + Abonemen         1.661.300
PPN              11% dari Subtotal                182.743
TOTAL TAGIHAN    Subtotal + PPN                   1.844.043
─────────────────────────────────────────────────────
```

## ✅ Validasi

Formula ini telah divalidasi dengan:
- ✅ Panduan perhitungan PLN resmi
- ✅ Contoh tagihan PLN aktual
- ✅ Perhitungan manual untuk berbagai skenario

## 🔍 Troubleshooting

### Error: "Tarif kelas tidak valid"
- Pastikan `PLN_TARIFF_CLASS` adalah salah satu: R1, R2, B2, I3
- Case sensitive: gunakan huruf besar

### Hasil tidak sesuai tagihan PLN
1. Cek golongan tarif yang digunakan
2. Pastikan konsumsi energi (kWh) sudah benar
3. Bandingkan dengan tagihan PLN aktual
4. Perhatikan periode billing (tanggal mulai-akhir)

### Import Error
```python
# Pastikan file pln_calculator.py ada di folder dashboard/
from pln_calculator import PLNTariffCalculator
```

## 📚 Referensi

- File: `dashboard/pln_calculator.py` - Implementasi kalkulator
- File: `PLN_CALCULATION_GUIDE.md` - Panduan lengkap perhitungan PLN
- File: `dashboard/report_generator.py` - Integrasi di reporting

---

**Last Updated:** 2024-11-18  
**Version:** 1.0

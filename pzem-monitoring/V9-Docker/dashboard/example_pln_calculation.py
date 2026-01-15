#!/usr/bin/env python3
"""
Contoh Penggunaan Formula Perhitungan PLN
Demonstrasi cara menggunakan PLN calculator di sistem reporting
"""

from pln_calculator import PLNTariffCalculator, calculate_pln_bill
from report_generator import ThreePhaseCalculator
import os

def example_1_basic_usage():
    """Contoh 1: Penggunaan dasar"""
    print("=" * 60)
    print("CONTOH 1: Penggunaan Dasar - R1, Konsumsi 1.200 kWh")
    print("=" * 60)
    
    energy_kwh = 1200.0
    bill = calculate_pln_bill(energy_kwh=energy_kwh, tariff_class='R1')
    
    print(f"\nKonsumsi Energi: {bill['energy_kwh']:.3f} kWh")
    print(f"\nBreakdown Perhitungan:")
    print(f"   Blok 1: {bill['block1_energy_kwh']:.3f} kWh × Rp 1.352/kWh = Rp {bill['block1_cost_idr']:,.0f}")
    print(f"   Blok 2: {bill['block2_energy_kwh']:.3f} kWh × Rp 1.445/kWh = Rp {bill['block2_cost_idr']:,.0f}")
    print(f"   " + "-" * 47)
    print(f"   Biaya Energi:                    Rp {bill['energy_cost_idr']:,.0f}")
    print(f"   Abonemen:                        Rp {bill['abonemen_idr']:,.0f}")
    print(f"   " + "-" * 47)
    print(f"   Subtotal:                        Rp {bill['subtotal_idr']:,.0f}")
    print(f"   PPN ({bill['ppn_percent']:.0f}%):                        Rp {bill['ppn_amount_idr']:,.0f}")
    print(f"   " + "-" * 47)
    print(f"   >>> TOTAL TAGIHAN PLN:            Rp {bill['total_bill_idr']:,.0f}")
    print()


def example_2_different_tariff_classes():
    """Contoh 2: Perbandingan berbagai golongan tarif"""
    print("=" * 60)
    print("CONTOH 2: Perbandingan Golongan Tarif (Konsumsi 1.000 kWh)")
    print("=" * 60)
    
    energy_kwh = 1000.0
    tariff_classes = ['R1', 'R2', 'B2', 'I3']
    
    results = []
    for tariff_class in tariff_classes:
        bill = calculate_pln_bill(energy_kwh=energy_kwh, tariff_class=tariff_class)
        results.append({
            'class': tariff_class,
            'total': bill['total_bill_idr']
        })
    
    print(f"\nKonsumsi: {energy_kwh:.0f} kWh\n")
    print(f"{'Golongan':<10} {'Total Tagihan':<20}")
    print("-" * 30)
    for r in results:
        print(f"{r['class']:<10} Rp {r['total']:>15,.0f}")
    print()


def example_3_using_calculator_class():
    """Contoh 3: Menggunakan class langsung"""
    print("=" * 60)
    print("CONTOH 3: Menggunakan PLNTariffCalculator Class")
    print("=" * 60)
    
    calculator = PLNTariffCalculator(tariff_class='R1')
    result = calculator.calculate_bill(energy_kwh=800)
    
    print(f"\nInfo Tarif: {result.tariff_class}")
    print(f"   Blok 1: 0-{calculator.config.block1_threshold:.0f} kWh @ Rp {calculator.config.block1_rate:,}/kWh")
    print(f"   Blok 2: >{calculator.config.block1_threshold:.0f} kWh @ Rp {calculator.config.block2_rate:,}/kWh")
    print(f"   Abonemen: Rp {calculator.config.abonemen:,}/bulan")
    print(f"\nTagihan untuk {result.energy_kwh:.0f} kWh:")
    print(f"   Total: Rp {result.total_bill:,.0f}")
    print()


def example_4_from_environment():
    """Contoh 4: Menggunakan environment variables"""
    print("=" * 60)
    print("CONTOH 4: Menggunakan Environment Variables")
    print("=" * 60)
    
    # Set environment (untuk contoh)
    os.environ['PLN_TARIFF_CLASS'] = 'R1'
    os.environ['PLN_PPN_PERCENT'] = '0.11'
    
    calculator = PLNTariffCalculator.from_environment()
    tariff_info = calculator.get_tariff_info()
    
    print(f"\nKonfigurasi dari Environment:")
    print(f"   Golongan: {tariff_info['tariff_class']}")
    print(f"   Blok 1: 0-{tariff_info['block1_threshold_kwh']:.0f} kWh @ Rp {tariff_info['block1_rate_rp_per_kwh']:,}/kWh")
    print(f"   Blok 2: >{tariff_info['block1_threshold_kwh']:.0f} kWh @ Rp {tariff_info['block2_rate_rp_per_kwh']:,}/kWh")
    print(f"   Abonemen: Rp {tariff_info['abonemen_rp']:,}")
    print(f"   PPN: {tariff_info['ppn_percent']:.0f}%")
    print()


def example_5_integration_with_reporting():
    """Contoh 5: Integrasi dengan sistem reporting"""
    print("=" * 60)
    print("CONTOH 5: Integrasi dengan Report Generator")
    print("=" * 60)
    
    # Simulasi data dari database
    total_energy_kwh = 1200.0
    
    # Menggunakan fungsi dari ThreePhaseCalculator
    pln_billing = ThreePhaseCalculator.calculate_pln_billing(
        total_energy_kwh=total_energy_kwh,
        tariff_class='R1'
    )
    
    print(f"\nData dari Sistem Monitoring:")
    print(f"   Total Energi: {pln_billing['energy_kwh']:.3f} kWh")
    print(f"\nPerhitungan Tagihan PLN:")
    print(f"   Golongan: {pln_billing['tariff_class']}")
    print(f"   Blok 1: {pln_billing['block1_energy_kwh']:.3f} kWh")
    print(f"   Blok 2: {pln_billing['block2_energy_kwh']:.3f} kWh")
    print(f"   Total Tagihan: Rp {pln_billing['total_bill_idr']:,.0f}")
    print()


def example_6_validation_scenarios():
    """Contoh 6: Skenario validasi dengan tagihan PLN aktual"""
    print("=" * 60)
    print("CONTOH 6: Skenario Validasi")
    print("=" * 60)
    
    test_cases = [
        {'energy': 500, 'expected': 762570, 'desc': 'R1, 500 kWh (hanya blok 1)'},
        {'energy': 1200, 'expected': 1844043, 'desc': 'R1, 1200 kWh (blok 1 + 2)'},
        {'energy': 2000, 'expected': 2890043, 'desc': 'R1, 2000 kWh (blok 1 + 2 besar)'},
    ]
    
    print(f"\n{'Konsumsi':<10} {'Hasil':<20} {'Expected':<20} {'Status':<10}")
    print("-" * 70)
    
    for case in test_cases:
        bill = calculate_pln_bill(energy_kwh=case['energy'], tariff_class='R1')
        actual = bill['total_bill_idr']
        expected = case['expected']
        diff = abs(actual - expected)
        status = "[OK]" if diff < 1 else f"[SELISIH: {diff:,.0f}]"
        
        print(f"{case['energy']:<10.0f} Rp {actual:>15,.0f}  Rp {expected:>15,.0f}  {status}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CONTOH PENGGUNAAN FORMULA PERHITUNGAN PLN")
    print("=" * 60 + "\n")
    
    example_1_basic_usage()
    example_2_different_tariff_classes()
    example_3_using_calculator_class()
    example_4_from_environment()
    example_5_integration_with_reporting()
    example_6_validation_scenarios()
    
    print("\n" + "=" * 60)
    print("SELESAI")
    print("=" * 60 + "\n")

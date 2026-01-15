#!/usr/bin/env python3
"""
PLN Tariff Calculator
Menghitung tagihan PLN berdasarkan sistem tarif blok (block tariff)
Kompatibel dengan sistem monitoring PZEM 004T
"""

from typing import Dict, Optional
from dataclasses import dataclass
import os


@dataclass
class PLNTariffConfig:
    """Konfigurasi tarif PLN per golongan"""
    tariff_class: str  # R1, R2, B2, I3
    block1_threshold: float  # Threshold untuk blok 1 (kWh)
    block1_rate: float  # Tarif blok 1 (Rp/kWh)
    block2_rate: float  # Tarif blok 2 (Rp/kWh)
    abonemen: float  # Abonemen bulanan (Rp)
    is_flat_rate: bool = False  # True untuk tarif flat (I3)


@dataclass
class PLNBillCalculation:
    """Hasil perhitungan tagihan PLN"""
    energy_kwh: float
    block1_energy: float
    block2_energy: float
    block1_cost: float
    block2_cost: float
    energy_cost: float
    abonemen: float
    subtotal: float
    ppn_percent: float
    ppn_amount: float
    total_bill: float
    tariff_class: str
    breakdown: Dict[str, float]


class PLNTariffCalculator:
    """Kalkulator tarif PLN dengan sistem blok"""
    
    # Konfigurasi tarif PLN 2024
    TARIFF_CONFIGS = {
        'R1': PLNTariffConfig(
            tariff_class='R1',
            block1_threshold=900,
            block1_rate=1352,
            block2_rate=1445,
            abonemen=11000,
            is_flat_rate=False
        ),
        'R2': PLNTariffConfig(
            tariff_class='R2',
            block1_threshold=1300,
            block1_rate=1352,
            block2_rate=1445,
            abonemen=20000,
            is_flat_rate=False
        ),
        'B2': PLNTariffConfig(
            tariff_class='B2',
            block1_threshold=200,
            block1_rate=1445,
            block2_rate=1699,
            abonemen=40000,
            is_flat_rate=False
        ),
        'I3': PLNTariffConfig(
            tariff_class='I3',
            block1_threshold=0,
            block1_rate=1699,
            block2_rate=1699,
            abonemen=40000,
            is_flat_rate=True
        )
    }
    
    # PPN default 11%
    DEFAULT_PPN = 0.11
    
    def __init__(self, tariff_class: str = 'R1', ppn_percent: float = None):
        """
        Inisialisasi kalkulator
        
        Args:
            tariff_class: Golongan tarif (R1, R2, B2, I3)
            ppn_percent: Persentase PPN (default: 11% atau dari env)
        """
        self.tariff_class = tariff_class.upper()
        
        if self.tariff_class not in self.TARIFF_CONFIGS:
            raise ValueError(f"Tarif kelas tidak valid: {tariff_class}. Pilih: R1, R2, B2, I3")
        
        self.config = self.TARIFF_CONFIGS[self.tariff_class]
        
        # PPN bisa dari environment variable atau parameter
        if ppn_percent is None:
            ppn_percent = float(os.getenv('PLN_PPN_PERCENT', self.DEFAULT_PPN))
        
        self.ppn_percent = ppn_percent
    
    def calculate_bill(self, energy_kwh: float) -> PLNBillCalculation:
        """
        Hitung tagihan PLN berdasarkan konsumsi energi
        
        Args:
            energy_kwh: Total konsumsi energi dalam kWh
            
        Returns:
            PLNBillCalculation: Objek berisi detail perhitungan
        """
        if energy_kwh < 0:
            raise ValueError("Konsumsi energi tidak boleh negatif")
        
        # Untuk tarif flat (I3)
        if self.config.is_flat_rate:
            block1_energy = energy_kwh
            block2_energy = 0
            block1_cost = energy_kwh * self.config.block1_rate
            block2_cost = 0
        else:
            # Hitung energi per blok
            block1_energy = min(energy_kwh, self.config.block1_threshold)
            block2_energy = max(0, energy_kwh - self.config.block1_threshold)
            
            # Hitung biaya per blok
            block1_cost = block1_energy * self.config.block1_rate
            block2_cost = block2_energy * self.config.block2_rate
        
        # Total biaya energi
        energy_cost = block1_cost + block2_cost
        
        # Tambah abonemen
        subtotal = energy_cost + self.config.abonemen
        
        # Hitung PPN
        ppn_amount = subtotal * self.ppn_percent
        
        # Total tagihan
        total_bill = subtotal + ppn_amount
        
        # Breakdown detail
        breakdown = {
            'block1_energy_kwh': block1_energy,
            'block2_energy_kwh': block2_energy,
            'block1_cost_idr': block1_cost,
            'block2_cost_idr': block2_cost,
            'energy_cost_idr': energy_cost,
            'abonemen_idr': self.config.abonemen,
            'subtotal_idr': subtotal,
            'ppn_percent': self.ppn_percent * 100,
            'ppn_amount_idr': ppn_amount,
            'total_bill_idr': total_bill
        }
        
        return PLNBillCalculation(
            energy_kwh=energy_kwh,
            block1_energy=block1_energy,
            block2_energy=block2_energy,
            block1_cost=block1_cost,
            block2_cost=block2_cost,
            energy_cost=energy_cost,
            abonemen=self.config.abonemen,
            subtotal=subtotal,
            ppn_percent=self.ppn_percent * 100,
            ppn_amount=ppn_amount,
            total_bill=total_bill,
            tariff_class=self.tariff_class,
            breakdown=breakdown
        )
    
    def calculate_energy_cost(self, energy_kwh: float) -> Dict[str, float]:
        """
        Hitung biaya energi saja (tanpa abonemen dan PPN)
        Kompatibel dengan fungsi calculate_energy_cost di report_generator.py
        
        Args:
            energy_kwh: Total konsumsi energi dalam kWh
            
        Returns:
            Dict dengan keys: energy_kwh, cost_idr, tariff_per_kwh
        """
        calculation = self.calculate_bill(energy_kwh)
        
        # Rata-rata tarif per kWh (untuk kompatibilitas)
        if energy_kwh > 0:
            avg_tariff = calculation.energy_cost / energy_kwh
        else:
            avg_tariff = self.config.block1_rate
        
        return {
            'energy_kwh': energy_kwh,
            'cost_idr': calculation.energy_cost,
            'tariff_per_kwh': avg_tariff,
            'total_bill_idr': calculation.total_bill,
            'breakdown': calculation.breakdown
        }
    
    def get_tariff_info(self) -> Dict:
        """Dapatkan informasi tarif yang sedang digunakan"""
        return {
            'tariff_class': self.tariff_class,
            'block1_threshold_kwh': self.config.block1_threshold,
            'block1_rate_rp_per_kwh': self.config.block1_rate,
            'block2_rate_rp_per_kwh': self.config.block2_rate,
            'abonemen_rp': self.config.abonemen,
            'is_flat_rate': self.config.is_flat_rate,
            'ppn_percent': self.ppn_percent * 100
        }
    
    @classmethod
    def from_environment(cls) -> 'PLNTariffCalculator':
        """
        Buat kalkulator dari environment variables
        
        Environment variables:
            PLN_TARIFF_CLASS: R1, R2, B2, I3 (default: R1)
            PLN_PPN_PERCENT: Persentase PPN (default: 0.11 = 11%)
        """
        tariff_class = os.getenv('PLN_TARIFF_CLASS', 'R1')
        ppn_percent = os.getenv('PLN_PPN_PERCENT')
        
        if ppn_percent:
            ppn_percent = float(ppn_percent)
        
        return cls(tariff_class=tariff_class, ppn_percent=ppn_percent)


# Fungsi helper untuk kompatibilitas dengan kode yang ada
def calculate_pln_bill(energy_kwh: float, tariff_class: str = 'R1', ppn_percent: float = None) -> Dict:
    """
    Fungsi helper untuk menghitung tagihan PLN
    
    Args:
        energy_kwh: Total konsumsi energi dalam kWh
        tariff_class: Golongan tarif (R1, R2, B2, I3)
        ppn_percent: Persentase PPN (default: 11%)
        
    Returns:
        Dict berisi detail perhitungan tagihan
    """
    calculator = PLNTariffCalculator(tariff_class=tariff_class, ppn_percent=ppn_percent)
    calculation = calculator.calculate_bill(energy_kwh)
    
    return {
        'energy_kwh': calculation.energy_kwh,
        'block1_energy_kwh': calculation.block1_energy,
        'block2_energy_kwh': calculation.block2_energy,
        'block1_cost_idr': calculation.block1_cost,
        'block2_cost_idr': calculation.block2_cost,
        'energy_cost_idr': calculation.energy_cost,
        'abonemen_idr': calculation.abonemen,
        'subtotal_idr': calculation.subtotal,
        'ppn_percent': calculation.ppn_percent,
        'ppn_amount_idr': calculation.ppn_amount,
        'total_bill_idr': calculation.total_bill,
        'tariff_class': calculation.tariff_class,
        'breakdown': calculation.breakdown
    }


# Contoh penggunaan
if __name__ == "__main__":
    print("=== PLN Tariff Calculator Test ===\n")
    
    # Test 1: R1 dengan konsumsi 1200 kWh
    print("Test 1: R1, Konsumsi 1200 kWh")
    calculator_r1 = PLNTariffCalculator('R1')
    result = calculator_r1.calculate_bill(1200)
    
    print(f"Energi: {result.energy_kwh} kWh")
    print(f"Blok 1: {result.block1_energy} kWh × Rp {calculator_r1.config.block1_rate:,} = Rp {result.block1_cost:,.0f}")
    print(f"Blok 2: {result.block2_energy} kWh × Rp {calculator_r1.config.block2_rate:,} = Rp {result.block2_cost:,.0f}")
    print(f"Biaya Energi: Rp {result.energy_cost:,.0f}")
    print(f"Abonemen: Rp {result.abonemen:,.0f}")
    print(f"Subtotal: Rp {result.subtotal:,.0f}")
    print(f"PPN ({result.ppn_percent}%): Rp {result.ppn_amount:,.0f}")
    print(f"TOTAL TAGIHAN: Rp {result.total_bill:,.0f}\n")
    
    # Test 2: R1 dengan konsumsi 500 kWh
    print("Test 2: R1, Konsumsi 500 kWh")
    result2 = calculator_r1.calculate_bill(500)
    print(f"TOTAL TAGIHAN: Rp {result2.total_bill:,.0f}\n")
    
    # Test 3: B2 dengan konsumsi 500 kWh
    print("Test 3: B2, Konsumsi 500 kWh")
    calculator_b2 = PLNTariffCalculator('B2')
    result3 = calculator_b2.calculate_bill(500)
    print(f"TOTAL TAGIHAN: Rp {result3.total_bill:,.0f}\n")
    
    # Test 4: I3 (flat rate) dengan konsumsi 1000 kWh
    print("Test 4: I3 (Flat Rate), Konsumsi 1000 kWh")
    calculator_i3 = PLNTariffCalculator('I3')
    result4 = calculator_i3.calculate_bill(1000)
    print(f"TOTAL TAGIHAN: Rp {result4.total_bill:,.0f}\n")
    
    # Test 5: Fungsi helper
    print("Test 5: Menggunakan fungsi helper")
    bill = calculate_pln_bill(1200, 'R1')
    print(f"TOTAL TAGIHAN: Rp {bill['total_bill_idr']:,.0f}")

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
    abonemen: float  # Abonemen bulanan tetap (Rp) — R1/R2
    is_flat_rate: bool = False  # True untuk tarif flat (B2/TR, I3)
    uses_rekening_minimum: bool = False  # True untuk B-2/TR (RM = 40 jam × kVA × tarif)
    description: str = ''


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
            block1_threshold=0,
            block1_rate=1444.7,
            block2_rate=1444.7,
            abonemen=0,
            is_flat_rate=True,
            uses_rekening_minimum=True,
            description='B-2/TR daya 6.600 VA–200 kVA (termasuk 33.000–53.000 VA)'
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
    
    def __init__(self, tariff_class: str = 'B2', ppn_percent: float = None, contracted_va: float = None):
        """
        Inisialisasi kalkulator
        
        Args:
            tariff_class: Golongan tarif (R1, R2, B2, I3)
            ppn_percent: Persentase PPN (default: 11% atau dari env)
            contracted_va: Daya kontrak (VA) untuk B-2/TR — default dari env PLN_CONTRACTED_VA (53.000)
        """
        self.tariff_class = tariff_class.upper()
        
        if self.tariff_class not in self.TARIFF_CONFIGS:
            raise ValueError(f"Tarif kelas tidak valid: {tariff_class}. Pilih: R1, R2, B2, I3")
        
        self.config = self.TARIFF_CONFIGS[self.tariff_class]
        
        # PPN bisa dari environment variable atau parameter
        if ppn_percent is None:
            ppn_percent = float(os.getenv('PLN_PPN_PERCENT', self.DEFAULT_PPN))
        
        self.ppn_percent = ppn_percent

        if contracted_va is None and self.config.uses_rekening_minimum:
            contracted_va = float(os.getenv('PLN_CONTRACTED_VA', '53000'))
        self.contracted_va = contracted_va
    
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
        
        rekening_minimum = 0.0
        rm_applied = False

        if self.config.uses_rekening_minimum:
            # B-2/TR: tarif flat + Rekening Minimum (RM1)
            # RM = 40 jam × daya (kVA) × tarif per kWh
            block1_energy = energy_kwh
            block2_energy = 0
            block1_cost = energy_kwh * self.config.block1_rate
            block2_cost = 0
            energy_cost = block1_cost
            kva = (self.contracted_va or 53000) / 1000.0
            rekening_minimum = 40 * kva * self.config.block1_rate
            subtotal = max(energy_cost, rekening_minimum)
            rm_applied = energy_cost < rekening_minimum
            abonemen = rekening_minimum
        elif self.config.is_flat_rate:
            block1_energy = energy_kwh
            block2_energy = 0
            block1_cost = energy_kwh * self.config.block1_rate
            block2_cost = 0
            energy_cost = block1_cost
            subtotal = energy_cost + self.config.abonemen
            abonemen = self.config.abonemen
        else:
            block1_energy = min(energy_kwh, self.config.block1_threshold)
            block2_energy = max(0, energy_kwh - self.config.block1_threshold)
            block1_cost = block1_energy * self.config.block1_rate
            block2_cost = block2_energy * self.config.block2_rate
            energy_cost = block1_cost + block2_cost
            subtotal = energy_cost + self.config.abonemen
            abonemen = self.config.abonemen
        
        ppn_amount = subtotal * self.ppn_percent
        total_bill = subtotal + ppn_amount
        
        breakdown = {
            'block1_energy_kwh': block1_energy,
            'block2_energy_kwh': block2_energy,
            'block1_cost_idr': block1_cost,
            'block2_cost_idr': block2_cost,
            'energy_cost_idr': energy_cost,
            'abonemen_idr': abonemen,
            'rekening_minimum_idr': rekening_minimum,
            'rm_applied': rm_applied,
            'contracted_va': self.contracted_va,
            'contracted_kva': (self.contracted_va or 0) / 1000.0 if self.contracted_va else None,
            'uses_rekening_minimum': self.config.uses_rekening_minimum,
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
            abonemen=abonemen,
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
        info = {
            'tariff_class': self.tariff_class,
            'description': self.config.description,
            'block1_threshold_kwh': self.config.block1_threshold,
            'block1_rate_rp_per_kwh': self.config.block1_rate,
            'block2_rate_rp_per_kwh': self.config.block2_rate,
            'abonemen_rp': self.config.abonemen,
            'is_flat_rate': self.config.is_flat_rate,
            'uses_rekening_minimum': self.config.uses_rekening_minimum,
            'ppn_percent': self.ppn_percent * 100
        }
        if self.config.uses_rekening_minimum and self.contracted_va:
            kva = self.contracted_va / 1000.0
            rm = 40 * kva * self.config.block1_rate
            info['contracted_va'] = self.contracted_va
            info['contracted_kva'] = kva
            info['rekening_minimum_rp'] = rm
        return info
    
    @classmethod
    def from_environment(cls) -> 'PLNTariffCalculator':
        """
        Buat kalkulator dari environment variables
        
        Environment variables:
            PLN_TARIFF_CLASS: R1, R2, B2, I3 (default: B2)
            PLN_CONTRACTED_VA: Daya kontrak VA untuk B-2/TR (default: 53000)
            PLN_PPN_PERCENT: Persentase PPN (default: 0.11 = 11%)
        """
        tariff_class = os.getenv('PLN_TARIFF_CLASS', 'B2')
        ppn_percent = os.getenv('PLN_PPN_PERCENT')
        contracted_va = os.getenv('PLN_CONTRACTED_VA')
        
        if ppn_percent:
            ppn_percent = float(ppn_percent)
        if contracted_va:
            contracted_va = float(contracted_va)
        
        return cls(tariff_class=tariff_class, ppn_percent=ppn_percent, contracted_va=contracted_va)


# Fungsi helper untuk kompatibilitas dengan kode yang ada
def calculate_pln_bill(
    energy_kwh: float,
    tariff_class: str = 'B2',
    ppn_percent: float = None,
    contracted_va: float = None
) -> Dict:
    """
    Fungsi helper untuk menghitung tagihan PLN
    
    Args:
        energy_kwh: Total konsumsi energi dalam kWh
        tariff_class: Golongan tarif (R1, R2, B2, I3)
        ppn_percent: Persentase PPN (default: 11%)
        contracted_va: Daya kontrak (VA) untuk B-2/TR
        
    Returns:
        Dict berisi detail perhitungan tagihan
    """
    calculator = PLNTariffCalculator(
        tariff_class=tariff_class,
        ppn_percent=ppn_percent,
        contracted_va=contracted_va
    )
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
    
    # Test 3: B2/TR 53.000 VA dengan konsumsi 500 kWh
    print("Test 3: B2/TR 53.000 VA, Konsumsi 500 kWh")
    calculator_b2 = PLNTariffCalculator('B2', contracted_va=53000)
    result3 = calculator_b2.calculate_bill(500)
    rm = 40 * 53 * 1444.7
    print(f"  RM: Rp {rm:,.0f}, Biaya pemakaian: Rp {result3.energy_cost:,.0f}")
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

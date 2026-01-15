#!/usr/bin/env python3
"""
PDF Report Generator for PZEM 3-Phase Energy Monitoring
Enhanced version with better error handling and clean code structure
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import tempfile
import os
import numpy as np
import math
import logging
import pytz
from pln_calculator import PLNTariffCalculator, calculate_pln_bill

# Database config - PASTIKAN SAMA dengan mqtt_client.py
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'pzem_monitoring'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASS', 'Admin123')
}
logger = logging.getLogger(__name__)

class ThreePhaseCalculator:
    """Kelas untuk perhitungan listrik 3 fasa"""
    
    @staticmethod
    def calculate_three_phase_power(phase_data):
        """Hitung total daya 3 fasa"""
        total_active_power = 0
        total_apparent_power = 0
        total_reactive_power = 0
        
        for phase in phase_data.values():
            # Safe float conversion dengan default values
            voltage = float(phase.get('avg_voltage', 0) or 0)
            current = float(phase.get('avg_current', 0) or 0)
            power = float(phase.get('avg_power', 0) or 0)
            power_factor = float(phase.get('avg_power_factor', 1.0) or 1.0)
            
            # Clamp power factor to valid range
            power_factor = max(0.0, min(1.0, power_factor))
            
            # Active Power (sudah ada)
            active_power = power
            total_active_power += active_power
            
            # Apparent Power (S = V × I)
            apparent_power = voltage * current
            total_apparent_power += apparent_power
            
            # Reactive Power (Q = S × sin(cos⁻¹(PF)))
            if power_factor > 0 and apparent_power > 0:
                try:
                    angle = math.acos(min(power_factor, 1.0))
                    reactive_power = apparent_power * math.sin(angle)
                except (ValueError, ZeroDivisionError):
                    reactive_power = 0
            else:
                reactive_power = 0
            total_reactive_power += reactive_power
        
        # Total Power Factor
        if total_apparent_power > 0:
            total_power_factor = total_active_power / total_apparent_power
        else:
            total_power_factor = 1.0
            
        return {
            'total_active_power': total_active_power,
            'total_apparent_power': total_apparent_power,
            'total_reactive_power': total_reactive_power,
            'total_power_factor': min(1.0, max(0.0, total_power_factor)),  # Clamp to valid range
            'efficiency_percentage': (min(1.0, max(0.0, total_power_factor)) * 100)
        }
    
    @staticmethod
    def calculate_phase_imbalance(phase_data):
        """Hitung ketidakseimbangan beban 3 fasa"""
        powers = []
        currents = []
        voltages = []
        
        for phase in phase_data.values():
            powers.append(float(phase.get('avg_power', 0) or 0))
            currents.append(float(phase.get('avg_current', 0) or 0))
            voltages.append(float(phase.get('avg_voltage', 0) or 0))
        
        # Handle empty lists
        if not powers:
            powers = [0]
        if not currents:
            currents = [0]  
        if not voltages:
            voltages = [0]
        
        # Hitung rata-rata dan standar deviasi
        avg_power = np.mean(powers) if powers else 0
        avg_current = np.mean(currents) if currents else 0
        avg_voltage = np.mean(voltages) if voltages else 0
        
        power_imbalance = (np.std(powers) / avg_power * 100) if avg_power > 0 else 0
        current_imbalance = (np.std(currents) / avg_current * 100) if avg_current > 0 else 0
        voltage_imbalance = (np.std(voltages) / avg_voltage * 100) if avg_voltage > 0 else 0
        
        return {
            'power_imbalance_percent': power_imbalance,
            'current_imbalance_percent': current_imbalance,
            'voltage_imbalance_percent': voltage_imbalance,
            'phase_powers': powers,
            'phase_currents': currents,
            'phase_voltages': voltages,
            'avg_power': avg_power,
            'avg_current': avg_current,
            'avg_voltage': avg_voltage
        }
    
    @staticmethod
    def calculate_energy_cost(total_energy_kwh, tariff_per_kwh=1500):
        """
        Hitung biaya energi (tariff dalam Rupiah per kWh)
        DEPRECATED: Gunakan calculate_pln_billing untuk perhitungan PLN yang akurat
        """
        total_cost = total_energy_kwh * tariff_per_kwh
        return {
            'energy_kwh': total_energy_kwh,
            'cost_idr': total_cost,
            'tariff_per_kwh': tariff_per_kwh
        }
    
    @staticmethod
    def calculate_pln_billing(total_energy_kwh, tariff_class=None, ppn_percent=None):
        """
        Hitung tagihan PLN berdasarkan sistem tarif blok (block tariff)
        
        Args:
            total_energy_kwh: Total konsumsi energi dalam kWh
            tariff_class: Golongan tarif PLN (R1, R2, B2, I3). 
                         Jika None, akan membaca dari env PLN_TARIFF_CLASS (default: R1)
            ppn_percent: Persentase PPN (default: 11% atau dari env PLN_PPN_PERCENT)
        
        Returns:
            Dict berisi detail perhitungan tagihan PLN:
            {
                'energy_kwh': float,
                'block1_energy_kwh': float,
                'block2_energy_kwh': float,
                'block1_cost_idr': float,
                'block2_cost_idr': float,
                'energy_cost_idr': float,
                'abonemen_idr': float,
                'subtotal_idr': float,
                'ppn_percent': float,
                'ppn_amount_idr': float,
                'total_bill_idr': float,
                'tariff_class': str,
                'breakdown': dict
            }
        """
        # Gunakan fungsi helper dari pln_calculator
        if tariff_class is None:
            tariff_class = os.getenv('PLN_TARIFF_CLASS', 'R1')
        
        return calculate_pln_bill(total_energy_kwh, tariff_class=tariff_class, ppn_percent=ppn_percent)

class DatabaseManager:
    def __init__(self):
        self.connection = None
    
    def get_connection(self):
        """Get a fresh database connection for each operation"""
        try:
            # Always create a new connection for report generation
            # This avoids conflicts with the main app's connection pool
            connection = psycopg2.connect(**DB_CONFIG)
            logger.debug("Created fresh database connection for reporting")
            return connection
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise ConnectionError(f"Failed to connect to database: {e}")
    
    def close_connection(self, connection):
        """Close a specific database connection"""
        try:
            if connection and not connection.closed:
                connection.close()
                logger.debug("Database connection closed")
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
    
    def ensure_table_structure(self):
        """Ensure table structure is correct"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Add missing columns if they don't exist
            cursor.execute("""
                ALTER TABLE pzem_data 
                ADD COLUMN IF NOT EXISTS frequency DECIMAL(6,2) DEFAULT 50.0;
            """)
            
            cursor.execute("""
                ALTER TABLE pzem_data 
                ADD COLUMN IF NOT EXISTS power_factor DECIMAL(5,3) DEFAULT 1.0;
            """)
            
            # Update NULL values
            cursor.execute("""
                UPDATE pzem_data 
                SET frequency = 50.0 
                WHERE frequency IS NULL;
            """)
            
            cursor.execute("""
                UPDATE pzem_data 
                SET power_factor = 1.0 
                WHERE power_factor IS NULL;
            """)
            
            conn.commit()
            cursor.close()
            logger.info("Table structure verified and updated")
            
        except Exception as e:
            logger.error(f"Error ensuring table structure: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.close_connection(conn)
    
    def get_report_data(self, period_type='daily', start_date=None, end_date=None):
        """Get data for report generation with simplified queries to avoid hanging"""
        conn = None
        try:
            logger.info("Starting simplified report data query")
            
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Set connection timeout
            cursor.execute("SET statement_timeout = '30s'")
            
            # Determine period if not provided
            if not end_date:
                end_date = datetime.now()
            
            if not start_date:
                if period_type == 'daily':
                    start_date = end_date - timedelta(days=1)
                elif period_type == 'weekly':
                    start_date = end_date - timedelta(weeks=1)
                elif period_type == 'monthly':
                    start_date = end_date - timedelta(days=30)
            
            logger.info(f"Querying data from {start_date} to {end_date}")
            
            # Simple check for data availability
            cursor.execute("SELECT COUNT(*) as total FROM pzem_data LIMIT 1")
            total_records = cursor.fetchone()['total']
            logger.info(f"Total records in database: {total_records}")
            
            if total_records == 0:
                logger.warning("No data found in database")
                return {
                    'period_type': period_type,
                    'start_date': start_date,
                    'end_date': end_date,
                    'phase_data': [],
                    'time_series': []
                }
            
            # Phase data query with accurate energy calculation
            # Energy calculation: 
            # 1. Primary: Use energy counter difference (MAX - MIN) if valid
            # 2. Fallback: Calculate from power using time-weighted integration
            simple_query = """
            WITH energy_data AS (
                SELECT 
                    device_address,
                    created_at,
                    COALESCE(power, 0) as power,
                    COALESCE(energy, 0) as energy,
                    LAG(created_at) OVER (PARTITION BY device_address ORDER BY created_at) as prev_time,
                    LAG(COALESCE(power, 0)) OVER (PARTITION BY device_address ORDER BY created_at) as prev_power
                FROM pzem_data 
                WHERE created_at >= %s AND created_at <= %s
            ),
            energy_calc AS (
                SELECT 
                    device_address,
                    -- Calculate energy from power using trapezoidal integration
                    SUM(
                        CASE 
                            WHEN prev_time IS NOT NULL AND prev_time < created_at
                            THEN (
                                (power + prev_power) / 2.0 * 
                                EXTRACT(EPOCH FROM (created_at - prev_time)) / 3600.0 / 1000.0
                            )
                            ELSE 0
                        END
                    ) as energy_from_power
                FROM energy_data
                GROUP BY device_address
            )
            SELECT 
                p.device_address,
                COUNT(*) as total_records,
                AVG(COALESCE(p.voltage, 220)) as avg_voltage,
                AVG(COALESCE(p.current, 0)) as avg_current,
                AVG(COALESCE(p.power, 0)) as avg_power,
                AVG(COALESCE(p.frequency, 50)) as avg_frequency,
                AVG(COALESCE(p.power_factor, 1)) as avg_power_factor,
                CASE 
                    -- Method 1: Use energy counter if available and valid (most accurate)
                    -- Check if energy counter is valid (not reset, reasonable value)
                    WHEN MAX(p.energy) IS NOT NULL AND MIN(p.energy) IS NOT NULL 
                         AND MAX(p.energy) >= MIN(p.energy)
                         AND (MAX(p.energy) - MIN(p.energy)) >= 0
                         AND (MAX(p.energy) - MIN(p.energy)) < 10000  -- Sanity check: energy diff < 10000 kWh
                         AND COUNT(*) > 1  -- Need at least 2 records for valid calculation
                    THEN GREATEST(0, MAX(p.energy) - MIN(p.energy))
                    -- Method 2: Use calculated energy from power integration (more accurate than simple average)
                    WHEN ec.energy_from_power IS NOT NULL AND ec.energy_from_power > 0
                    THEN ec.energy_from_power
                    -- Method 3: Fallback to average power * duration (least accurate)
                    ELSE (
                        GREATEST(0, AVG(COALESCE(p.power, 0)) * 
                        EXTRACT(EPOCH FROM (MAX(p.created_at) - MIN(p.created_at))) / 3600.0 / 1000.0)
                    )
                END as energy_consumed,
                MIN(p.created_at) as period_start,
                MAX(p.created_at) as period_end,
                MAX(COALESCE(p.energy, 0)) as max_energy,
                MIN(COALESCE(p.energy, 0)) as min_energy
            FROM pzem_data p
            LEFT JOIN energy_calc ec ON p.device_address = ec.device_address
            WHERE p.created_at >= %s AND p.created_at <= %s
            GROUP BY p.device_address, ec.energy_from_power
            ORDER BY p.device_address
            LIMIT 10
            """
            
            logger.info("Executing phase data query with improved energy calculation...")
            cursor.execute(simple_query, (start_date, end_date, start_date, end_date))
            phase_data = cursor.fetchall()
            
            logger.info(f"Found {len(phase_data)} devices/phases")
            # Log energy calculation details for debugging
            for phase in phase_data:
                device = phase.get('device_address', 'Unknown')
                energy = phase.get('energy_consumed', 0)
                max_e = phase.get('max_energy', 0)
                min_e = phase.get('min_energy', 0)
                logger.debug(f"Device {device}: Energy={energy:.3f} kWh (counter: {min_e:.3f}->{max_e:.3f})")
            
            # Simplified time series query - just get recent points
            time_series_query = """
            SELECT 
                DATE_TRUNC('hour', created_at) as time_period,
                device_address,
                AVG(COALESCE(power, 0)) as power,
                AVG(COALESCE(voltage, 220)) as voltage,
                AVG(COALESCE(current, 0)) as current,
                COUNT(*) as sample_count
            FROM pzem_data 
            WHERE created_at >= %s AND created_at <= %s
            GROUP BY time_period, device_address
            ORDER BY time_period DESC, device_address
            LIMIT 100
            """
            
            logger.info("Executing time series query...")
            cursor.execute(time_series_query, (start_date, end_date))
            time_series_data = cursor.fetchall()
            
            logger.info(f"Found {len(time_series_data)} time series points")
            
            cursor.close()
            
            result = {
                'period_type': period_type,
                'start_date': start_date,
                'end_date': end_date,
                'phase_data': [dict(row) for row in phase_data],
                'time_series': [dict(row) for row in time_series_data]
            }
            
            logger.info("Successfully retrieved simplified report data")
            return result
            
        except Exception as e:
            logger.error(f"Error getting report data: {e}")
            # Return empty data structure instead of None
            return {
                'period_type': period_type,
                'start_date': start_date or datetime.now() - timedelta(days=1),
                'end_date': end_date or datetime.now(),
                'phase_data': [],
                'time_series': []
            }
        finally:
            if conn:
                self.close_connection(conn)

class ReportGenerator:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.styles = getSampleStyleSheet()
        
        # Custom styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1  # Center
        )
        
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
    
    def create_chart_image(self, data, chart_type='power_trend', filename=None):
        """Create charts and save as images with better error handling"""
        if not filename:
            filename = tempfile.mktemp(suffix='.png')
        
        try:
            plt.figure(figsize=(10, 6))
            plt.style.use('default')
            
            if chart_type == 'power_trend':
                self._create_power_trend_chart(data)
            elif chart_type == 'phase_distribution':
                self._create_phase_distribution_chart(data)
            else:
                raise ValueError(f"Unknown chart type: {chart_type}")
            
            plt.tight_layout()
            plt.savefig(filename, dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            plt.close()
            
            return filename
            
        except Exception as e:
            logger.error(f"Error creating {chart_type} chart: {e}")
            plt.close()  # Ensure plot is closed even on error
            return None
    
    def _create_power_trend_chart(self, data):
        """Create power trend line chart"""
        devices = {}
        for row in data.get('time_series', []):
            device = row['device_address']
            if device not in devices:
                devices[device] = {'times': [], 'powers': []}
            devices[device]['times'].append(row['time_period'])
            devices[device]['powers'].append(float(row['power'] or 0))
        
        if not devices:
            plt.text(0.5, 0.5, 'No Data Available', ha='center', va='center', 
                    transform=plt.gca().transAxes, fontsize=14)
            plt.title('Power Consumption Trend - No Data')
        else:
            colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']
            for i, (device, values) in enumerate(devices.items()):
                if values['times'] and values['powers']:
                    plt.plot(values['times'], values['powers'], 
                           label=f'Phase {device}', 
                           color=colors[i % len(colors)],
                           linewidth=2, marker='o', markersize=4)
            
            plt.title('Power Consumption Trend - All Phases', fontsize=14, fontweight='bold')
            plt.xlabel('Time', fontsize=12)
            plt.ylabel('Power (W)', fontsize=12)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
    
    def _create_phase_distribution_chart(self, data):
        """Create phase power distribution pie chart"""
        phases = []
        powers = []
        
        for phase in data.get('phase_data', []):
            phases.append(f"Phase {phase['device_address']}")
            power = float(phase.get('avg_power', 0) or 0)
            powers.append(max(0.01, power))  # Minimum 0.01 for visibility
        
        if not phases or sum(powers) <= 0:
            plt.text(0.5, 0.5, 'No Power Data Available', ha='center', va='center',
                    fontsize=14)
            plt.title('Power Distribution by Phase - No Data')
        else:
            colors_pie = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57']
            plt.pie(powers, labels=phases, autopct='%1.1f%%', 
                   colors=colors_pie[:len(powers)], startangle=90)
            plt.title('Power Distribution by Phase', fontsize=14, fontweight='bold')
    
    def generate_report(self, period_type='daily', start_date=None, end_date=None, output_file=None):
        """Generate comprehensive PDF report with enhanced error handling"""
        chart_files = []  # Track temporary files for cleanup
        
        try:
            # Get data from database
            logger.info(f"Fetching report data for period: {period_type}")
            data = self.db_manager.get_report_data(period_type, start_date, end_date)
            if not data:
                logger.error("No data available for report generation")
                return None
            
            # Generate report even with no phase data (will show "no data" message)
            phase_count = len(data.get('phase_data', []))
            time_series_count = len(data.get('time_series', []))
            logger.info(f"Retrieved data: {phase_count} phases, {time_series_count} time series points")
            
            if phase_count == 0:
                logger.warning("No phase data found, generating empty report")
            
            # Setup PDF - create in reports directory
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                reports_dir = os.path.join(os.getcwd(), 'reports')
                os.makedirs(reports_dir, exist_ok=True)
                output_file = os.path.join(reports_dir, f"PZEM_Report_{period_type}_{timestamp}.pdf")
            
            doc = SimpleDocTemplate(output_file, pagesize=A4)
            story = []
            
            # Title
            title = f"PZEM 3-Phase Energy Monitoring Report<br/>{period_type.title()} Report"
            story.append(Paragraph(title, self.title_style))
            story.append(Spacer(1, 20))
            
            # Period info
            period_info = f"""
            <b>Report Period:</b> {data['start_date'].strftime('%Y-%m-%d %H:%M')} to {data['end_date'].strftime('%Y-%m-%d %H:%M')}<br/>
            <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
            <b>Total Phases:</b> {len(data['phase_data'])}
            """
            story.append(Paragraph(period_info, self.normal_style))
            story.append(Spacer(1, 20))
            
            # Executive Summary dengan perhitungan 3 fasa
            story.append(Paragraph("EXECUTIVE SUMMARY", self.heading_style))
            
            # Convert phase_data to dict with device_address as key
            phase_dict = {}
            total_energy = 0
            
            for phase in data.get('phase_data', []):
                device_addr = phase['device_address']
                phase_dict[device_addr] = phase
                energy = float(phase.get('energy_consumed', 0) or 0)
                total_energy += energy
            
            # Calculate 3-phase metrics with safe handling
            if phase_dict:
                logger.info("Calculating 3-phase metrics")
                three_phase_power = ThreePhaseCalculator.calculate_three_phase_power(phase_dict)
                phase_imbalance = ThreePhaseCalculator.calculate_phase_imbalance(phase_dict)
                
                # Gunakan perhitungan PLN yang akurat
                pln_billing = ThreePhaseCalculator.calculate_pln_billing(total_energy)
                tariff_class = pln_billing.get('tariff_class', 'R1')
                
                summary_data = [
                    ['Parameter', 'Value', 'Unit'],
                    ['Total Active Power', f"{three_phase_power['total_active_power']:.2f}", 'W'],
                    ['Total Apparent Power', f"{three_phase_power['total_apparent_power']:.2f}", 'VA'],
                    ['Total Reactive Power', f"{three_phase_power['total_reactive_power']:.2f}", 'VAR'],
                    ['Overall Power Factor', f"{three_phase_power['total_power_factor']:.3f}", '-'],
                    ['System Efficiency', f"{three_phase_power['efficiency_percentage']:.1f}", '%'],
                    ['Total Energy Consumed', f"{total_energy:.3f}", 'kWh'],
                    ['Tariff Class', tariff_class, '-'],
                    ['Energy Cost (Blok 1+2)', f"Rp {pln_billing['energy_cost_idr']:,.0f}", 'IDR'],
                    ['Abonemen', f"Rp {pln_billing['abonemen_idr']:,.0f}", 'IDR'],
                    ['PPN ({:.0f}%)'.format(pln_billing['ppn_percent']), f"Rp {pln_billing['ppn_amount_idr']:,.0f}", 'IDR'],
                    ['TOTAL TAGIHAN PLN', f"Rp {pln_billing['total_bill_idr']:,.0f}", 'IDR'],
                    ['Power Imbalance', f"{phase_imbalance['power_imbalance_percent']:.1f}", '%'],
                    ['Current Imbalance', f"{phase_imbalance['current_imbalance_percent']:.1f}", '%'],
                    ['Voltage Imbalance', f"{phase_imbalance['voltage_imbalance_percent']:.1f}", '%']
                ]
            else:
                logger.warning("No phase data available, using default values")
                summary_data = [
                    ['Parameter', 'Value', 'Unit'],
                    ['Total Active Power', '0.00', 'W'],
                    ['Total Apparent Power', '0.00', 'VA'],
                    ['Total Reactive Power', '0.00', 'VAR'],
                    ['Overall Power Factor', '0.000', '-'],
                    ['System Efficiency', '0.0', '%'],
                    ['Total Energy Consumed', '0.000', 'kWh'],
                    ['Tariff Class', '-', '-'],
                    ['Energy Cost (Blok 1+2)', 'Rp 0', 'IDR'],
                    ['Abonemen', 'Rp 0', 'IDR'],
                    ['PPN (11%)', 'Rp 0', 'IDR'],
                    ['TOTAL TAGIHAN PLN', 'Rp 0', 'IDR'],
                    ['Power Imbalance', '0.0', '%'],
                    ['Current Imbalance', '0.0', '%'],
                    ['Voltage Imbalance', '0.0', '%']
                ]
            
            summary_table = Table(summary_data)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 20))
            
            # Phase Detail Analysis
            story.append(Paragraph("DETAILED PHASE ANALYSIS", self.heading_style))
            
            phase_detail_data = [['Phase', 'Avg Voltage (V)', 'Avg Current (A)', 'Avg Power (W)', 
                                 'Energy (kWh)', 'Power Factor', 'Records']]
            
            if data.get('phase_data'):
                for phase in data['phase_data']:
                    phase_detail_data.append([
                        f"Phase {phase['device_address']}",
                        f"{float(phase.get('avg_voltage', 0) or 0):.1f}",
                        f"{float(phase.get('avg_current', 0) or 0):.3f}",
                        f"{float(phase.get('avg_power', 0) or 0):.2f}",
                        f"{float(phase.get('energy_consumed', 0) or 0):.3f}",
                        f"{float(phase.get('avg_power_factor', 1) or 1):.3f}",
                        str(phase.get('total_records', 0))
                    ])
            else:
                phase_detail_data.append([
                    "No Data Available", "-", "-", "-", "-", "-", "0"
                ])
            
            phase_table = Table(phase_detail_data)
            phase_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(phase_table)
            story.append(Spacer(1, 20))
            
            # PLN Billing Breakdown (jika ada data energi)
            if phase_dict and total_energy > 0:
                story.append(Paragraph("PLN BILLING BREAKDOWN", self.heading_style))
                
                pln_billing = ThreePhaseCalculator.calculate_pln_billing(total_energy)
                breakdown = pln_billing.get('breakdown', {})
                
                # Dapatkan info tarif
                tariff_class = pln_billing.get('tariff_class', 'R1')
                calculator = PLNTariffCalculator(tariff_class=tariff_class)
                tariff_info = calculator.get_tariff_info()
                
                # Tabel breakdown detail
                billing_detail_data = [
                    ['Item', 'Detail', 'Amount (Rp)'],
                    ['Total Konsumsi', f"{pln_billing['energy_kwh']:.3f} kWh", '-'],
                    ['Blok 1', 
                     f"{pln_billing['block1_energy_kwh']:.3f} kWh × Rp {tariff_info['block1_rate_rp_per_kwh']:,}/kWh",
                     f"{pln_billing['block1_cost_idr']:,.0f}"],
                    ['Blok 2', 
                     f"{pln_billing['block2_energy_kwh']:.3f} kWh × Rp {tariff_info['block2_rate_rp_per_kwh']:,}/kWh",
                     f"{pln_billing['block2_cost_idr']:,.0f}"],
                    ['Biaya Energi', 'Blok 1 + Blok 2', f"{pln_billing['energy_cost_idr']:,.0f}"],
                    ['Abonemen', f"Golongan {tariff_class}", f"{pln_billing['abonemen_idr']:,.0f}"],
                    ['Subtotal', 'Biaya Energi + Abonemen', f"{pln_billing['subtotal_idr']:,.0f}"],
                    ['PPN', f"{pln_billing['ppn_percent']:.0f}% dari Subtotal", f"{pln_billing['ppn_amount_idr']:,.0f}"],
                    ['TOTAL TAGIHAN', 'Subtotal + PPN', f"{pln_billing['total_bill_idr']:,.0f}"]
                ]
                
                billing_table = Table(billing_detail_data, colWidths=[120, 250, 100])
                billing_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, -1), (-1, -1), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.lightgrey),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.darkgreen),
                    ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey])
                ]))
                
                story.append(billing_table)
                story.append(Spacer(1, 10))
                
                # Info tarif yang digunakan
                tariff_info_text = f"""
                <b>Info Tarif:</b> Golongan {tariff_class}<br/>
                Blok 1: 0-{tariff_info['block1_threshold_kwh']:.0f} kWh → Rp {tariff_info['block1_rate_rp_per_kwh']:,}/kWh<br/>
                Blok 2: >{tariff_info['block1_threshold_kwh']:.0f} kWh → Rp {tariff_info['block2_rate_rp_per_kwh']:,}/kWh<br/>
                Abonemen: Rp {tariff_info['abonemen_rp']:,}/bulan<br/>
                PPN: {tariff_info['ppn_percent']:.0f}%
                """
                story.append(Paragraph(tariff_info_text, self.normal_style))
                story.append(Spacer(1, 20))
            
            # Charts (if data available)
            if data['time_series'] and len(data['time_series']) > 0:
                logger.info("Creating charts for report")
                story.append(Paragraph("POWER CONSUMPTION TRENDS", self.heading_style))
                
                # Create power trend chart
                logger.info("Generating power trend chart")
                chart_file = self.create_chart_image(data, 'power_trend')
                if chart_file and os.path.exists(chart_file):
                    chart_files.append(chart_file)  # Track for cleanup
                    img = RLImage(chart_file, width=500, height=300)
                    story.append(img)
                    story.append(Spacer(1, 20))
                    logger.info("Power trend chart added to report")
                else:
                    logger.warning("Power trend chart generation failed")
                    story.append(Paragraph("Chart generation failed", self.normal_style))
                
                # Page break before next chart
                story.append(PageBreak())
                
                # Create phase distribution chart
                story.append(Paragraph("POWER DISTRIBUTION BY PHASE", self.heading_style))
                logger.info("Generating phase distribution chart")
                dist_chart_file = self.create_chart_image(data, 'phase_distribution')
                if dist_chart_file and os.path.exists(dist_chart_file):
                    chart_files.append(dist_chart_file)  # Track for cleanup
                    img2 = RLImage(dist_chart_file, width=400, height=300)
                    story.append(img2)
                    story.append(Spacer(1, 20))
                    logger.info("Phase distribution chart added to report")
                else:
                    logger.warning("Phase distribution chart generation failed")
                    story.append(Paragraph("Distribution chart generation failed", self.normal_style))
            else:
                story.append(Paragraph("CHARTS", self.heading_style))
                story.append(Paragraph("No time series data available for charts", self.normal_style))
                story.append(Spacer(1, 20))
            
            # Load Analysis
            story.append(Paragraph("LOAD ANALYSIS & RECOMMENDATIONS", self.heading_style))
            
            # Generate recommendations based on data
            if phase_dict:
                recommendations = self.generate_recommendations(three_phase_power, phase_imbalance, data['phase_data'])
            else:
                recommendations = ["No data available for recommendations"]
            
            for rec in recommendations:
                story.append(Paragraph(f"• {rec}", self.normal_style))
            
            story.append(Spacer(1, 20))
            
            # Footer
            footer_text = f"""
            <br/><br/>
            <i>This report was automatically generated by PZEM 3-Phase Monitoring System<br/>
            Report generation time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
            Database records processed: {sum(p.get('total_records', 0) for p in data['phase_data'])}</i>
            """
            story.append(Paragraph(footer_text, self.normal_style))
            
            # Build PDF document
            logger.info("Building PDF document...")
            doc.build(story)
            logger.info(f"Report generated successfully: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        
        finally:
            # Cleanup temporary chart files
            for chart_file in chart_files:
                try:
                    if chart_file and os.path.exists(chart_file):
                        os.unlink(chart_file)
                        logger.debug(f"Cleaned up temporary file: {chart_file}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup file {chart_file}: {cleanup_error}")
    
    def generate_recommendations(self, power_data, imbalance_data, phase_data):
        """Generate recommendations based on data analysis"""
        recommendations = []
        
        try:
            # Power factor analysis
            if power_data['total_power_factor'] < 0.85:
                recommendations.append("Low power factor detected. Consider installing power factor correction capacitors to improve efficiency.")
            elif power_data['total_power_factor'] > 0.95:
                recommendations.append("Excellent power factor maintained. System is operating efficiently.")
            
            # Phase imbalance analysis
            if imbalance_data['power_imbalance_percent'] > 20:
                recommendations.append("High power imbalance detected. Redistribute loads across phases to improve system stability.")
            elif imbalance_data['current_imbalance_percent'] > 15:
                recommendations.append("Current imbalance is significant. Check for faulty equipment or uneven load distribution.")
            
            # Voltage analysis
            if imbalance_data['voltage_imbalance_percent'] > 5:
                recommendations.append("Voltage imbalance exceeds recommended limits. Contact utility provider or check transformer connections.")
            
            # Individual phase analysis
            for phase in phase_data:
                avg_voltage = float(phase.get('avg_voltage', 0) or 0)
                if avg_voltage > 0:
                    if avg_voltage < 200 or avg_voltage > 240:
                        recommendations.append(f"Phase {phase['device_address']}: Voltage ({avg_voltage:.1f}V) is outside normal range (200-240V).")
            
            # Energy efficiency
            total_power = power_data['total_active_power']
            if total_power > 0:
                if power_data['efficiency_percentage'] > 90:
                    recommendations.append("System operating at high efficiency. Maintain current operating conditions.")
                else:
                    recommendations.append("System efficiency can be improved. Review load management and power quality.")
            
            # Default recommendation if none specific
            if not recommendations:
                recommendations.append("System is operating within normal parameters. Continue regular monitoring.")
        
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations = ["Unable to generate recommendations due to data analysis error."]
        
        return recommendations

def main():
    """Main function untuk testing"""
    try:
        print("Testing PZEM Report Generator...")
        
        # Initialize
        db_manager = DatabaseManager()
        report_gen = ReportGenerator(db_manager)
        
        # Test database connection
        print("Testing database connection...")
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pzem_data")
        count = cursor.fetchone()[0]
        print(f"Found {count} records in database")
        cursor.close()
        
        if count == 0:
            print("No data in database. Please run MQTT client first to collect data.")
            return
        
        # Generate test report
        print("Generating test daily report...")
        daily_report = report_gen.generate_report('daily')
        if daily_report:
            print(f"SUCCESS: Daily report generated: {daily_report}")
        else:
            print("FAILED: Could not generate daily report")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
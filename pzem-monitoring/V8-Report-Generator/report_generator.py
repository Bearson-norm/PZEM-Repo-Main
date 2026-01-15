#!/usr/bin/env python3
"""
Fixed PDF Report Generator untuk PZEM 3-Phase Energy Monitoring
Windows Compatible - Tanpa emoji - With better error handling
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Line, Rect, Circle
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.widgetbase import Widget
from reportlab.graphics import renderPDF
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import tempfile
import os
import numpy as np
import math
import logging

# Database config - PASTIKAN SAMA dengan mqtt_client.py
DB_CONFIG = {
    'host': 'localhost',
    'database': 'pzem_monitoring', 
    'user': 'postgres',
    'password': 'Admin123'
}

logging.basicConfig(level=logging.INFO)
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
        """Hitung biaya energi (tariff dalam Rupiah per kWh)"""
        total_cost = total_energy_kwh * tariff_per_kwh
        return {
            'energy_kwh': total_energy_kwh,
            'cost_idr': total_cost,
            'tariff_per_kwh': tariff_per_kwh
        }

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            logger.info("Connected to database for reporting")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    def get_connection(self):
        if self.connection is None or self.connection.closed:
            self.connect()
        return self.connection
    
    def ensure_table_structure(self):
        """Pastikan struktur tabel sesuai dengan yang diharapkan"""
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
    
    def get_report_data(self, period_type='daily', start_date=None, end_date=None):
        """Ambil data untuk laporan dengan periode tertentu - IMPROVED"""
        try:
            # Ensure table structure first
            self.ensure_table_structure()
            
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Tentukan periode jika tidak diberikan
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
            
            # First check if we have ANY data
            cursor.execute("SELECT COUNT(*) as total FROM pzem_data")
            total_records = cursor.fetchone()['total']
            logger.info(f"Total records in database: {total_records}")
            
            if total_records == 0:
                logger.warning("No data found in database")
                return None
            
            # Check data in time range
            cursor.execute("""
                SELECT COUNT(*) as count FROM pzem_data 
                WHERE created_at >= %s AND created_at <= %s
            """, (start_date, end_date))
            
            range_records = cursor.fetchone()['count']
            logger.info(f"Records in time range: {range_records}")
            
            if range_records == 0:
                # If no data in range, get the most recent data instead
                logger.warning("No data in specified range, getting recent data")
                cursor.execute("""
                    SELECT MIN(created_at) as oldest, MAX(created_at) as newest 
                    FROM pzem_data
                """)
                time_range = cursor.fetchone()
                start_date = time_range['oldest']
                end_date = time_range['newest']
                logger.info(f"Using actual data range: {start_date} to {end_date}")
            
            # Query data agregat per device (fasa) dengan safe handling
            query = """
            SELECT 
                device_address,
                COUNT(*) as total_records,
                COALESCE(AVG(voltage), 0) as avg_voltage,
                COALESCE(AVG(current), 0) as avg_current,
                COALESCE(AVG(power), 0) as avg_power,
                COALESCE(AVG(frequency), 50.0) as avg_frequency,
                COALESCE(AVG(power_factor), 1.0) as avg_power_factor,
                COALESCE(MAX(energy) - MIN(energy), 0) as energy_consumed,
                MIN(created_at) as period_start,
                MAX(created_at) as period_end,
                COALESCE(MIN(voltage), 0) as min_voltage,
                COALESCE(MAX(voltage), 0) as max_voltage,
                COALESCE(MIN(current), 0) as min_current,
                COALESCE(MAX(current), 0) as max_current,
                COALESCE(MIN(power), 0) as min_power,
                COALESCE(MAX(power), 0) as max_power
            FROM pzem_data 
            WHERE created_at >= %s AND created_at <= %s
            GROUP BY device_address
            ORDER BY device_address
            """
            
            cursor.execute(query, (start_date, end_date))
            phase_data = cursor.fetchall()
            
            logger.info(f"Found {len(phase_data)} devices/phases")
            for phase in phase_data:
                logger.info(f"Device {phase['device_address']}: {phase['total_records']} records, {phase['avg_power']:.1f}W avg")
            
            # Query data time series untuk grafik
            if period_type == 'daily':
                time_group = "DATE_TRUNC('hour', created_at)"
                interval = '1 hour'
            elif period_type == 'weekly':
                time_group = "DATE_TRUNC('day', created_at)"
                interval = '1 day'
            else:  # monthly
                time_group = "DATE_TRUNC('day', created_at)"
                interval = '1 day'
            
            time_series_query = f"""
            SELECT 
                {time_group} as time_period,
                device_address,
                COALESCE(AVG(voltage), 0) as voltage,
                COALESCE(AVG(current), 0) as current,
                COALESCE(AVG(power), 0) as power,
                COUNT(*) as sample_count
            FROM pzem_data 
            WHERE created_at >= %s AND created_at <= %s
            GROUP BY time_period, device_address
            HAVING COUNT(*) > 0
            ORDER BY time_period, device_address
            """
            
            cursor.execute(time_series_query, (start_date, end_date))
            time_series_data = cursor.fetchall()
            
            cursor.close()
            
            return {
                'period_type': period_type,
                'start_date': start_date,
                'end_date': end_date,
                'phase_data': [dict(row) for row in phase_data],
                'time_series': [dict(row) for row in time_series_data]
            }
            
        except Exception as e:
            logger.error(f"Error getting report data: {e}")
            # Try to get basic info for debugging
            try:
                conn = self.get_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT COUNT(*) as total FROM pzem_data")
                total = cursor.fetchone()['total']
                logger.error(f"Debug: Total records in DB: {total}")
                cursor.close()
            except:
                pass
            return None

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
        """Buat grafik dan simpan sebagai gambar - IMPROVED"""
        try:
            if not filename:
                filename = tempfile.mktemp(suffix='.png')
            
            plt.figure(figsize=(10, 6))
            plt.style.use('default')
            
            if chart_type == 'power_trend':
                # Group data by device for line chart
                devices = {}
                for row in data['time_series']:
                    device = row['device_address']
                    if device not in devices:
                        devices[device] = {'times': [], 'powers': []}
                    devices[device]['times'].append(row['time_period'])
                    devices[device]['powers'].append(float(row['power'] or 0))
                
                if not devices:
                    # Create dummy chart if no data
                    plt.text(0.5, 0.5, 'No Data Available', ha='center', va='center', transform=plt.gca().transAxes)
                    plt.title('Power Consumption Trend - No Data')
                else:
                    # Plot each phase
                    colors = ['blue', 'red', 'green', 'orange', 'purple']
                    for i, (device, values) in enumerate(devices.items()):
                        if values['times'] and values['powers']:
                            plt.plot(values['times'], values['powers'], 
                                   label=f'Phase {device}', 
                                   color=colors[i % len(colors)],
                                   linewidth=2, marker='o', markersize=4)
                    
                    plt.title('Power Consumption Trend - All Phases')
                    plt.xlabel('Time')
                    plt.ylabel('Power (W)')
                    plt.legend()
                    plt.grid(True, alpha=0.3)
                    plt.xticks(rotation=45)
                
            elif chart_type == 'phase_distribution':
                # Pie chart untuk distribusi daya per fasa
                phases = []
                powers = []
                
                for phase in data['phase_data']:
                    phases.append(f"Phase {phase['device_address']}")
                    power = float(phase['avg_power'] or 0)
                    powers.append(max(0.1, power))  # Minimum 0.1 for visibility
                
                if not phases or sum(powers) == 0:
                    plt.text(0.5, 0.5, 'No Power Data Available', ha='center', va='center')
                    plt.title('Power Distribution by Phase - No Data')
                else:
                    colors_pie = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57']
                    plt.pie(powers, labels=phases, autopct='%1.1f%%', colors=colors_pie[:len(powers)])
                    plt.title('Power Distribution by Phase')
                
            plt.tight_layout()
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.close()
            
            return filename
            
        except Exception as e:
            logger.error(f"Error creating chart: {e}")
            return None
    
    def generate_report(self, period_type='daily', start_date=None, end_date=None, output_file=None):
        """Generate laporan PDF lengkap - IMPROVED with better error handling"""
        try:
            # Get data
            data = self.db_manager.get_report_data(period_type, start_date, end_date)
            if not data:
                logger.error("No data available for report generation")
                return None
            
            if not data['phase_data']:
                logger.error("No phase data available for report generation")
                return None
            
            # Setup PDF
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"PZEM_Report_{period_type}_{timestamp}.pdf"
            
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
            
            for phase in data['phase_data']:
                device_addr = phase['device_address']
                phase_dict[device_addr] = phase
                energy = float(phase.get('energy_consumed', 0) or 0)
                total_energy += energy
            
            # Perhitungan 3 fasa dengan safe handling
            if phase_dict:
                three_phase_power = ThreePhaseCalculator.calculate_three_phase_power(phase_dict)
                phase_imbalance = ThreePhaseCalculator.calculate_phase_imbalance(phase_dict)
                energy_cost = ThreePhaseCalculator.calculate_energy_cost(total_energy)
                
                summary_data = [
                    ['Parameter', 'Value', 'Unit'],
                    ['Total Active Power', f"{three_phase_power['total_active_power']:.2f}", 'W'],
                    ['Total Apparent Power', f"{three_phase_power['total_apparent_power']:.2f}", 'VA'],
                    ['Total Reactive Power', f"{three_phase_power['total_reactive_power']:.2f}", 'VAR'],
                    ['Overall Power Factor', f"{three_phase_power['total_power_factor']:.3f}", '-'],
                    ['System Efficiency', f"{three_phase_power['efficiency_percentage']:.1f}", '%'],
                    ['Total Energy Consumed', f"{total_energy:.3f}", 'kWh'],
                    ['Estimated Cost', f"Rp {energy_cost['cost_idr']:,.0f}", 'IDR'],
                    ['Power Imbalance', f"{phase_imbalance['power_imbalance_percent']:.1f}", '%'],
                    ['Current Imbalance', f"{phase_imbalance['current_imbalance_percent']:.1f}", '%'],
                    ['Voltage Imbalance', f"{phase_imbalance['voltage_imbalance_percent']:.1f}", '%']
                ]
            else:
                summary_data = [
                    ['Parameter', 'Value', 'Unit'],
                    ['Total Active Power', '0.00', 'W'],
                    ['Total Apparent Power', '0.00', 'VA'],
                    ['Total Reactive Power', '0.00', 'VAR'],
                    ['Overall Power Factor', '0.000', '-'],
                    ['System Efficiency', '0.0', '%'],
                    ['Total Energy Consumed', '0.000', 'kWh'],
                    ['Estimated Cost', 'Rp 0', 'IDR'],
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
            
            # Charts (if data available)
            if data['time_series'] and len(data['time_series']) > 0:
                story.append(Paragraph("POWER CONSUMPTION TRENDS", self.heading_style))
                
                # Create power trend chart
                chart_file = self.create_chart_image(data, 'power_trend')
                if chart_file and os.path.exists(chart_file):
                    img = RLImage(chart_file, width=500, height=300)
                    story.append(img)
                    story.append(Spacer(1, 20))
                else:
                    story.append(Paragraph("Chart generation failed", self.normal_style))
                
                # Page break before next chart
                story.append(PageBreak())
                
                # Create phase distribution chart
                story.append(Paragraph("POWER DISTRIBUTION BY PHASE", self.heading_style))
                dist_chart_file = self.create_chart_image(data, 'phase_distribution')
                if dist_chart_file and os.path.exists(dist_chart_file):
                    img2 = RLImage(dist_chart_file, width=400, height=300)
                    story.append(img2)
                    story.append(Spacer(1, 20))
                else:
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
            
            # Build PDF
            doc.build(story)
            
            # Cleanup temporary files
            try:
                if 'chart_file' in locals() and chart_file:
                    os.unlink(chart_file)
                if 'dist_chart_file' in locals() and dist_chart_file:
                    os.unlink(dist_chart_file)
            except:
                pass
            
            logger.info(f"Report generated successfully: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
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
#!/usr/bin/env python3
"""
Windows Compatible Flask Dashboard untuk PZEM - Dengan Report Integration
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, timedelta
import threading
import time
import logging
from decimal import Decimal

# Import report modules
from report_routes import report_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*", logger=False)

# Register report blueprint
app.register_blueprint(report_bp)

# Setup logging compatible dengan Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database config
DB_CONFIG = {
    'host': 'localhost',
    'database': 'pzem_monitoring',
    'user': 'postgres',
    'password': 'Admin123'
}

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            logger.info("[SUCCESS] Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"[ERROR] Database connection error: {e}")
    
    def get_connection(self):
        if self.connection is None or self.connection.closed:
            self.connect()
        return self.connection
    
    def serialize_data(self, data):
        """Convert datetime objects and Decimals to JSON serializable formats"""
        if isinstance(data, list):
            return [self.serialize_data(item) for item in data]
        elif isinstance(data, dict):
            return {key: self.serialize_data(value) for key, value in data.items()}
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, Decimal):
            return float(data)
        elif data is None:
            return None
        elif isinstance(data, (int, float, str, bool)):
            return data
        else:
            return str(data)
    
    def get_system_status(self):
        """Ambil status sistem keseluruhan dengan 3-phase calculations"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Total devices (phases)
            cursor.execute("SELECT COUNT(DISTINCT device_address) as total FROM pzem_data")
            total_devices = cursor.fetchone()['total'] or 0
            
            # Online devices (data dalam 10 menit terakhir)
            cursor.execute("""
                SELECT COUNT(DISTINCT device_address) as online 
                FROM pzem_data 
                WHERE created_at >= NOW() - INTERVAL '10 minutes'
            """)
            online_devices = cursor.fetchone()['online'] or 0
            
            # 3-Phase calculations dari data terbaru setiap device
            cursor.execute("""
                WITH latest_data AS (
                    SELECT DISTINCT ON (device_address) 
                        device_address, power, energy, voltage, current, 
                        power_factor, created_at
                    FROM pzem_data 
                    ORDER BY device_address, created_at DESC
                )
                SELECT 
                    device_address,
                    COALESCE(power, 0) as power,
                    COALESCE(energy, 0) as energy,
                    COALESCE(voltage, 0) as voltage,
                    COALESCE(current, 0) as current,
                    COALESCE(power_factor, 1.0) as power_factor,
                    created_at
                FROM latest_data
                WHERE created_at >= NOW() - INTERVAL '10 minutes'
            """)
            
            phase_data = cursor.fetchall()
            cursor.close()
            
            # Calculate 3-phase totals
            total_active_power = 0
            total_apparent_power = 0
            total_energy = 0
            total_current = 0
            avg_voltage = 0
            voltage_count = 0
            
            for phase in phase_data:
                power = float(phase['power'] or 0)
                energy = float(phase['energy'] or 0)
                voltage = float(phase['voltage'] or 0)
                current = float(phase['current'] or 0)
                
                total_active_power += power
                total_energy += energy
                total_current += current
                
                if voltage > 0:
                    avg_voltage += voltage
                    voltage_count += 1
                    # Apparent Power = V × I
                    total_apparent_power += voltage * current
            
            # Average voltage across phases
            if voltage_count > 0:
                avg_voltage = avg_voltage / voltage_count
            
            # Overall power factor
            overall_power_factor = (total_active_power / total_apparent_power) if total_apparent_power > 0 else 1.0
            
            return {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'total_active_power': round(total_active_power, 2),
                'total_apparent_power': round(total_apparent_power, 2),
                'total_energy': round(total_energy, 2),
                'overall_power_factor': round(overall_power_factor, 3),
                'avg_voltage': round(avg_voltage, 1),
                'total_current': round(total_current, 2),
                'system_efficiency': round(overall_power_factor * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting system status: {e}")
            return {
                'total_devices': 0,
                'online_devices': 0,
                'total_active_power': 0,
                'total_apparent_power': 0,
                'total_energy': 0,
                'overall_power_factor': 0,
                'avg_voltage': 0,
                'total_current': 0,
                'system_efficiency': 0
            }
    
    def get_devices(self):
        """Ambil daftar semua device dengan enhanced info"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
            SELECT 
                d.device_address,
                COALESCE(dm.device_name, 'Phase ' || d.device_address) as device_name,
                COALESCE(dm.location, 'Unknown') as location,
                COUNT(d.id) as data_count,
                MAX(d.created_at) as last_seen,
                AVG(d.power) as avg_power,
                AVG(d.voltage) as avg_voltage,
                AVG(d.current) as avg_current,
                AVG(d.power_factor) as avg_power_factor,
                MAX(d.energy) as total_energy,
                MIN(d.voltage) as min_voltage,
                MAX(d.voltage) as max_voltage,
                COALESCE(dm.status, 'active') as device_status
            FROM pzem_data d
            LEFT JOIN pzem_devices dm ON d.device_address = dm.device_address
            GROUP BY d.device_address, dm.device_name, dm.location, dm.status
            ORDER BY d.device_address
            """
            
            cursor.execute(query)
            devices = cursor.fetchall()
            cursor.close()
            
            return [self.serialize_data(dict(device)) for device in devices]
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting devices: {e}")
            return []
    
    def get_device_data(self, device_address, period='hour', limit=100):
        """Ambil data device berdasarkan periode"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            period_config = {
                'hour': {'interval': '1 hour', 'limit': 60},
                'day': {'interval': '1 day', 'limit': 144},
                'week': {'interval': '1 week', 'limit': 168},
                'month': {'interval': '1 month', 'limit': 120}
            }
            
            config = period_config.get(period, period_config['hour'])
            interval = config['interval']
            default_limit = config['limit']
            
            query = f"""
            SELECT 
                device_address, voltage, current, power, energy, frequency,
                power_factor, wifi_rssi, device_timestamp, sample_interval,
                device_status, data_quality, timestamp_utc, created_at
            FROM pzem_data 
            WHERE device_address = %s 
            AND created_at >= NOW() - INTERVAL '{interval}'
            ORDER BY created_at DESC
            LIMIT %s
            """
            
            cursor.execute(query, (device_address, limit or default_limit))
            data = cursor.fetchall()
            cursor.close()
            
            return [self.serialize_data(dict(row)) for row in data]
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting device data: {e}")
            return []
    
    def get_aggregated_data(self, device_address, period='hour'):
        """Ambil data agregat untuk grafik dengan power calculations"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            period_configs = {
                'hour': {
                    'interval': '1 hour',
                    'group_by': "DATE_TRUNC('minute', created_at)",
                },
                'day': {
                    'interval': '1 day', 
                    'group_by': "DATE_TRUNC('hour', created_at)",
                },
                'week': {
                    'interval': '1 week',
                    'group_by': "DATE_TRUNC('hour', created_at)", 
                },
                'month': {
                    'interval': '1 month',
                    'group_by': "DATE_TRUNC('day', created_at)",
                }
            }
            
            config = period_configs.get(period, period_configs['hour'])
            
            query = f"""
            SELECT 
                {config['group_by']} as time_period,
                AVG(voltage) as voltage,
                AVG(current) as current,
                AVG(power) as power,
                AVG(voltage * current) as apparent_power,
                MAX(energy) - MIN(energy) as energy_consumed,
                AVG(frequency) as frequency,
                AVG(power_factor) as power_factor,
                COUNT(*) as sample_count
            FROM pzem_data 
            WHERE device_address = %s 
            AND created_at >= NOW() - INTERVAL '{config['interval']}'
            GROUP BY time_period
            HAVING COUNT(*) > 0
            ORDER BY time_period ASC
            """
            
            cursor.execute(query, (device_address,))
            data = cursor.fetchall()
            cursor.close()
            
            return [self.serialize_data(dict(row)) for row in data]
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting aggregated data: {e}")
            return []
    
    def get_all_latest_data(self):
        """Ambil data terbaru dari semua device dengan enhanced calculations"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
            SELECT DISTINCT ON (device_address) 
                device_address,
                voltage,
                current,
                power,
                energy,
                frequency,
                power_factor,
                wifi_rssi,
                device_timestamp,
                device_status,
                data_quality,
                timestamp_utc,
                created_at,
                (voltage * current) as apparent_power,
                CASE 
                    WHEN power > 0 AND voltage > 0 AND current > 0 
                    THEN power / (voltage * current) 
                    ELSE power_factor 
                END as calculated_pf
            FROM pzem_data 
            ORDER BY device_address, created_at DESC
            """
            
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            
            logger.debug(f"[DATABASE] Retrieved {len(data)} devices from database")
            
            result = {}
            for row in data:
                try:
                    device_data = dict(row)
                    device_address = row['device_address']
                    
                    # Serialize data
                    serialized_data = self.serialize_data(device_data)
                    
                    # Test JSON serialization
                    json.dumps(serialized_data)
                    
                    result[device_address] = serialized_data
                    logger.debug(f"[DATABASE] Successfully serialized device {device_address}")
                    
                except Exception as device_error:
                    logger.error(f"[ERROR] Error serializing device {row.get('device_address', 'unknown')}: {device_error}")
                    continue
            
            logger.debug(f"[DATABASE] Final result contains {len(result)} devices")
            return result
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting all latest data: {e}")
            return {}

    def get_three_phase_summary(self):
        """Get 3-phase system summary for quick overview"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get latest data from last hour for stability
            query = """
            WITH latest_data AS (
                SELECT DISTINCT ON (device_address) 
                    device_address, power, voltage, current, power_factor, energy
                FROM pzem_data 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                ORDER BY device_address, created_at DESC
            )
            SELECT 
                COUNT(*) as total_phases,
                SUM(power) as total_active_power,
                SUM(voltage * current) as total_apparent_power,
                AVG(voltage) as avg_voltage,
                SUM(current) as total_current,
                SUM(energy) as total_energy,
                STDDEV(power) as power_stddev,
                STDDEV(voltage) as voltage_stddev,
                STDDEV(current) as current_stddev
            FROM latest_data
            WHERE power IS NOT NULL AND voltage IS NOT NULL AND current IS NOT NULL
            """
            
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                total_active = float(result['total_active_power'] or 0)
                total_apparent = float(result['total_apparent_power'] or 0)
                avg_power = total_active / max(result['total_phases'] or 1, 1)
                
                # Calculate imbalances
                power_imbalance = 0
                if avg_power > 0 and result['power_stddev']:
                    power_imbalance = (float(result['power_stddev']) / avg_power) * 100
                
                return {
                    'total_phases': result['total_phases'] or 0,
                    'total_active_power': round(total_active, 2),
                    'total_apparent_power': round(total_apparent, 2),
                    'overall_power_factor': round(total_active / total_apparent, 3) if total_apparent > 0 else 0,
                    'avg_voltage': round(float(result['avg_voltage'] or 0), 1),
                    'total_current': round(float(result['total_current'] or 0), 2),
                    'total_energy': round(float(result['total_energy'] or 0), 3),
                    'power_imbalance_percent': round(power_imbalance, 1),
                    'system_efficiency': round((total_active / total_apparent * 100), 1) if total_apparent > 0 else 0
                }
            else:
                return {}
                
        except Exception as e:
            logger.error(f"[ERROR] Error getting 3-phase summary: {e}")
            return {}

# Inisialisasi database manager
db_manager = DatabaseManager()

# Updated routes with enhanced calculations
@app.route('/')
def index():
    """Halaman utama dashboard dengan report link"""
    # Read the original template and add report navigation
    with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # Add report button to header
    enhanced_template = template_content.replace(
        '<p>Real-time Power Consumption Dashboard</p>',
        '''<p>Real-time Power Consumption Dashboard</p>
        <div style="margin-top: 15px;">
            <a href="/reports" style="background: linear-gradient(45deg, #28a745, #20c997); 
                                     color: white; padding: 10px 20px; text-decoration: none; 
                                     border-radius: 10px; font-weight: 600; display: inline-block; 
                                     transition: all 0.3s ease;">
                <i class="fas fa-file-pdf"></i> Generate Reports
            </a>
        </div>'''
    )
    
    return enhanced_template

@app.route('/api/system-status')
def api_system_status():
    """API untuk status sistem keseluruhan dengan 3-phase info"""
    try:
        status = db_manager.get_system_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"[ERROR] Error in system status API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/three-phase-summary')  
def api_three_phase_summary():
    """API untuk ringkasan sistem 3-fase"""
    try:
        summary = db_manager.get_three_phase_summary()
        return jsonify(summary)
    except Exception as e:
        logger.error(f"[ERROR] Error in 3-phase summary API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/devices')
def api_devices():
    """API untuk daftar semua device"""
    try:
        devices = db_manager.get_devices()
        return jsonify(devices)
    except Exception as e:
        logger.error(f"[ERROR] Error in devices API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/latest/<device_address>')
def api_latest_data(device_address):
    """API untuk data terbaru device tertentu"""
    try:
        data = db_manager.get_device_data(device_address, 'hour', 1)
        return jsonify(data[0] if data else {})
    except Exception as e:
        logger.error(f"[ERROR] Error in latest data API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/data/<device_address>')
def api_device_data(device_address):
    """API untuk data device dengan filter periode"""
    try:
        period = request.args.get('period', 'hour')
        limit = request.args.get('limit', 100, type=int)
        data = db_manager.get_device_data(device_address, period, limit)
        return jsonify(data)
    except Exception as e:
        logger.error(f"[ERROR] Error in device data API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/chart/<device_address>')
def api_chart_data(device_address):
    """API untuk data grafik device dengan power calculations"""
    try:
        period = request.args.get('period', 'hour')
        data = db_manager.get_aggregated_data(device_address, period)
        return jsonify(data)
    except Exception as e:
        logger.error(f"[ERROR] Error in chart data API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/all-latest')
def api_all_latest():
    """API untuk mendapatkan data terbaru semua device dengan calculations"""
    try:
        data = db_manager.get_all_latest_data()
        return jsonify(data)
    except Exception as e:
        logger.error(f"[ERROR] Error in all latest API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/export/<device_address>')
def api_export_data(device_address):
    """API untuk export data device"""
    try:
        period = request.args.get('period', 'day')
        data = db_manager.get_device_data(device_address, period, 1000)
        
        return jsonify({
            'device_address': device_address,
            'period': period,
            'total_records': len(data),
            'export_timestamp': datetime.now().isoformat(),
            'data': data
        })
    except Exception as e:
        logger.error(f"[ERROR] Error in export API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Enhanced WebSocket events with 3-phase data
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('[WEBSOCKET] Client connected')
    emit('connected', {'data': 'Connected to PZEM 3-Phase Dashboard'})
    
    # Send initial data with 3-phase summary
    try:
        latest_data = db_manager.get_all_latest_data()
        three_phase_summary = db_manager.get_three_phase_summary()
        
        emit('data_update', {
            'devices': latest_data,
            'summary': three_phase_summary
        })
        logger.debug(f"[WEBSOCKET] Sent initial data for {len(latest_data)} devices")
    except Exception as e:
        logger.error(f"[ERROR] Error sending initial data: {e}")
        emit('data_update', {'devices': {}, 'summary': {}})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('[WEBSOCKET] Client disconnected')

@socketio.on('subscribe_device')
def handle_subscribe_device(data):
    """Handle subscription to specific device updates"""
    device_address = data.get('device_address')
    logger.info(f'[WEBSOCKET] Client subscribed to device: {device_address}')

@socketio.on('request_chart_update')
def handle_chart_update_request(data):
    """Handle request for chart data update"""
    try:
        device_address = data.get('device_address')
        period = data.get('period', 'hour')
        
        if device_address:
            chart_data = db_manager.get_aggregated_data(device_address, period)
            emit('chart_update', {
                'device_address': device_address,
                'period': period,
                'data': chart_data
            })
    except Exception as e:
        logger.error(f"[ERROR] Error handling chart update request: {e}")
        emit('chart_update', {
            'device_address': data.get('device_address', ''),
            'period': data.get('period', 'hour'),
            'data': []
        })

# Enhanced background task dengan 3-phase calculations
def background_thread():
    """Background task yang mengirim data terbaru secara berkala"""
    logger.info("[BACKGROUND] Starting enhanced background data push thread")
    
    while True:
        try:
            logger.debug("[BACKGROUND] Fetching latest data from database...")
            latest_data = db_manager.get_all_latest_data()
            three_phase_summary = db_manager.get_three_phase_summary()
            
            if latest_data or three_phase_summary:
                combined_data = {
                    'devices': latest_data,
                    'summary': three_phase_summary,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.debug(f"[BACKGROUND] Retrieved data for {len(latest_data)} devices")
                
                # Test JSON serialization
                try:
                    json_test = json.dumps(combined_data)
                    logger.debug(f"[BACKGROUND] JSON serialization test passed ({len(json_test)} chars)")
                except Exception as json_error:
                    logger.error(f"[ERROR] JSON serialization test failed: {json_error}")
                    socketio.emit('data_update', {'devices': {}, 'summary': {}})
                    continue
                
                # Emit enhanced data
                socketio.emit('data_update', combined_data)
                logger.debug(f"[BACKGROUND] Successfully pushed enhanced data")
                
            else:
                logger.debug("[BACKGROUND] No data to push, emitting empty dict")
                socketio.emit('data_update', {'devices': {}, 'summary': {}})
            
        except Exception as e:
            logger.error(f"[ERROR] Error in background thread: {e}")
            try:
                socketio.emit('data_update', {'devices': {}, 'summary': {}})
                logger.debug("[BACKGROUND] Emitted empty data due to error")
            except Exception as emit_error:
                logger.error(f"[ERROR] Failed to emit error recovery data: {emit_error}")
        
        time.sleep(30)  # Update setiap 30 detik

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Enhanced health check
@app.route('/health')
def health_check():
    """Health check endpoint dengan 3-phase info"""
    try:
        # Test database connection
        system_status = db_manager.get_system_status()
        summary = db_manager.get_three_phase_summary()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'version': '3.0-three-phase-enhanced',
            'system_info': system_status,
            'three_phase_summary': summary,
            'features': [
                'real_time_monitoring',
                'three_phase_calculations', 
                'pdf_reporting',
                'power_analysis',
                'cost_estimation'
            ]
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy', 
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # Mulai background thread
    thread = threading.Thread(target=background_thread)
    thread.daemon = True
    thread.start()
    
    logger.info("[STARTING] PZEM 3-Phase Dashboard Server (Enhanced with Reporting)")
    logger.info("[WEBSOCKET] Listening for connections on port 5000")
    logger.info("[DATABASE] Using enhanced 3-phase database structure")
    logger.info("[REPORTS] PDF reporting system enabled")
    
    # Run the application
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5000, 
        debug=False,
        use_reloader=False
    )
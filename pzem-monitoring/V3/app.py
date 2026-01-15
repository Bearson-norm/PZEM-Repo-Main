#!/usr/bin/env python3
"""
Enhanced Flask Dashboard untuk monitoring data sensor PZEM secara realtime
Dengan fitur grafik dan tabel dinamis berdasarkan periode waktu
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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*", logger=True)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for detailed logging
    format='%(asctime)s - %(levelname)s - %(message)s'
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
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
    
    def get_connection(self):
        if self.connection is None or self.connection.closed:
            self.connect()
        return self.connection
    
    def get_system_status(self):
        """Ambil status sistem secara keseluruhan"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Hitung total devices
            cursor.execute("SELECT COUNT(DISTINCT device_address) as total FROM pzem_data")
            total_devices = cursor.fetchone()['total'] or 0
            
            # Hitung online devices (data dalam 10 menit terakhir)
            cursor.execute("""
                SELECT COUNT(DISTINCT device_address) as online 
                FROM pzem_data 
                WHERE created_at >= NOW() - INTERVAL '10 minutes'
            """)
            online_devices = cursor.fetchone()['online'] or 0
            
            # Total power dan energy dari data terbaru setiap device
            cursor.execute("""
                WITH latest_data AS (
                    SELECT DISTINCT ON (device_address) 
                        device_address, avg_power, total_energy, created_at
                    FROM pzem_data 
                    ORDER BY device_address, created_at DESC
                )
                SELECT 
                    COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '10 minutes' 
                                 THEN avg_power ELSE 0 END), 0) as total_power,
                    COALESCE(SUM(total_energy), 0) as total_energy
                FROM latest_data
            """)
            
            totals = cursor.fetchone()
            total_power = round(totals['total_power'] or 0, 2)
            total_energy = round(totals['total_energy'] or 0, 2)
            
            cursor.close()
            
            return {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'total_power': total_power,
                'total_energy': total_energy
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                'total_devices': 0,
                'online_devices': 0,
                'total_power': 0,
                'total_energy': 0
            }
    
    def get_devices(self):
        """Ambil daftar semua device dengan informasi lengkap"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
            SELECT 
                device_address,
                COUNT(*) as data_count,
                MAX(created_at) as last_seen,
                AVG(avg_power) as avg_power,
                AVG(avg_voltage) as avg_voltage,
                AVG(avg_current) as avg_current,
                SUM(total_energy) as total_energy
            FROM pzem_data 
            GROUP BY device_address
            ORDER BY device_address
            """
            
            cursor.execute(query)
            devices = cursor.fetchall()
            cursor.close()
            
            return [dict(device) for device in devices]
            
        except Exception as e:
            logger.error(f"Error getting devices: {e}")
            return []
    
    def get_device_data(self, device_address, period='hour', limit=100):
        """Ambil data device berdasarkan periode dengan limit yang fleksibel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Tentukan interval berdasarkan periode
            period_config = {
                'hour': {'interval': '1 hour', 'limit': 60},
                'day': {'interval': '1 day', 'limit': 144},  # setiap 10 menit
                'week': {'interval': '1 week', 'limit': 168}, # setiap jam
                'month': {'interval': '1 month', 'limit': 120} # setiap 6 jam
            }
            
            config = period_config.get(period, period_config['hour'])
            interval = config['interval']
            default_limit = config['limit']
            
            query = f"""
            SELECT * FROM pzem_data 
            WHERE device_address = %s 
            AND created_at >= NOW() - INTERVAL '{interval}'
            ORDER BY created_at DESC
            LIMIT %s
            """
            
            cursor.execute(query, (device_address, limit or default_limit))
            data = cursor.fetchall()
            cursor.close()
            
            return [dict(row) for row in data]
            
        except Exception as e:
            logger.error(f"Error getting device data: {e}")
            return []
    
    def get_aggregated_data(self, device_address, period='hour'):
        """Ambil data agregat untuk grafik dengan sampling yang optimal"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Konfigurasi untuk setiap periode
            period_configs = {
                'hour': {
                    'interval': '1 hour',
                    'group_by': "DATE_TRUNC('minute', created_at)",
                    'sample_interval': '1 minute'
                },
                'day': {
                    'interval': '1 day', 
                    'group_by': "DATE_TRUNC('hour', created_at)",
                    'sample_interval': '10 minutes'
                },
                'week': {
                    'interval': '1 week',
                    'group_by': "DATE_TRUNC('hour', created_at)", 
                    'sample_interval': '1 hour'
                },
                'month': {
                    'interval': '1 month',
                    'group_by': "DATE_TRUNC('day', created_at)",
                    'sample_interval': '6 hours'
                }
            }
            
            config = period_configs.get(period, period_configs['hour'])
            
            query = f"""
            SELECT 
                {config['group_by']} as time_period,
                AVG(avg_voltage) as voltage,
                AVG(avg_current) as current,
                AVG(avg_power) as power,
                MAX(total_energy) - MIN(total_energy) as energy,
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
            
            return [dict(row) for row in data]
            
        except Exception as e:
            logger.error(f"Error getting aggregated data: {e}")
            return []
    
    def get_all_latest_data(self):
        """Ambil data terbaru dari semua device"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
            SELECT DISTINCT ON (device_address) 
                device_address,
                timestamp_data,
                wifi_rssi,
                avg_voltage,
                avg_current, 
                avg_power,
                total_energy,
                current_voltage,
                current_current,
                current_active_power,
                current_power_factor,
                created_at
            FROM pzem_data 
            ORDER BY device_address, created_at DESC
            """
            
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            
            # Convert to dictionary with device_address as key
            result = {}
            for row in data:
                result[row['device_address']] = dict(row)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting all latest data: {e}")
            return {}
    
    def get_device_statistics(self, device_address, period='day'):
        """Ambil statistik device untuk periode tertentu"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            period_intervals = {
                'hour': '1 hour',
                'day': '1 day', 
                'week': '1 week',
                'month': '1 month'
            }
            
            interval = period_intervals.get(period, '1 day')
            
            query = f"""
            SELECT 
                device_address,
                COUNT(*) as total_records,
                AVG(avg_power) as avg_power,
                MIN(avg_power) as min_power,
                MAX(avg_power) as max_power,
                AVG(avg_voltage) as avg_voltage,
                MIN(avg_voltage) as min_voltage,
                MAX(avg_voltage) as max_voltage,
                AVG(avg_current) as avg_current,
                MIN(avg_current) as min_current,
                MAX(avg_current) as max_current,
                MAX(total_energy) - MIN(total_energy) as energy_consumed,
                MIN(created_at) as period_start,
                MAX(created_at) as period_end
            FROM pzem_data 
            WHERE device_address = %s 
            AND created_at >= NOW() - INTERVAL '{interval}'
            GROUP BY device_address
            """
            
            cursor.execute(query, (device_address,))
            data = cursor.fetchone()
            cursor.close()
            
            return dict(data) if data else {}
            
        except Exception as e:
            logger.error(f"Error getting device statistics: {e}")
            return {}

# Inisialisasi database manager
db_manager = DatabaseManager()

# Routes
@app.route('/')
def index():
    """Halaman utama dashboard"""
    return render_template('dashboard.html')

@app.route('/api/system-status')
def api_system_status():
    """API untuk status sistem keseluruhan"""
    try:
        status = db_manager.get_system_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error in system status API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/devices')
def api_devices():
    """API untuk daftar semua device"""
    try:
        devices = db_manager.get_devices()
        return jsonify(devices)
    except Exception as e:
        logger.error(f"Error in devices API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/latest/<device_address>')
def api_latest_data(device_address):
    """API untuk data terbaru device tertentu"""
    try:
        data = db_manager.get_device_data(device_address, 'hour', 1)
        return jsonify(data[0] if data else {})
    except Exception as e:
        logger.error(f"Error in latest data API: {e}")
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
        logger.error(f"Error in device data API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/chart/<device_address>')
def api_chart_data(device_address):
    """API untuk data grafik device"""
    try:
        period = request.args.get('period', 'hour')
        data = db_manager.get_aggregated_data(device_address, period)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in chart data API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/all-latest')
def api_all_latest():
    """API untuk mendapatkan data terbaru semua device"""
    try:
        data = db_manager.get_all_latest_data()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in all latest API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/statistics/<device_address>')
def api_device_statistics(device_address):
    """API untuk statistik device"""
    try:
        period = request.args.get('period', 'day')
        stats = db_manager.get_device_statistics(device_address, period)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error in statistics API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/export/<device_address>')
def api_export_data(device_address):
    """API untuk export data device dalam format JSON"""
    try:
        period = request.args.get('period', 'day')
        format_type = request.args.get('format', 'json')
        
        data = db_manager.get_device_data(device_address, period, 1000)
        
        if format_type == 'csv':
            # Implementation for CSV export would go here
            pass
        
        return jsonify({
            'device_address': device_address,
            'period': period,
            'total_records': len(data),
            'data': data
        })
    except Exception as e:
        logger.error(f"Error in export API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('connected', {'data': 'Connected to PZEM Dashboard'})
    
    # Send initial data
    try:
        latest_data = db_manager.get_all_latest_data()
        emit('data_update', latest_data)
    except Exception as e:
        logger.error(f"Error sending initial data: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

@socketio.on('subscribe_device')
def handle_subscribe_device(data):
    """Handle subscription to specific device updates"""
    device_address = data.get('device_address')
    logger.info(f'Client subscribed to device: {device_address}')
    # Could implement device-specific rooms here

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
        logger.error(f"Error handling chart update request: {e}")

# Background task untuk push data realtime
def background_thread():
    """Background task yang mengirim data terbaru secara berkala"""
    logger.info("Starting background data push thread")
    
    while True:
        try:
            # Ambil data terbaru semua device
            latest_data = db_manager.get_all_latest_data()
            
            if latest_data:
                # Emit ke semua client yang terhubung
                socketio.emit('data_update', latest_data)
                logger.debug(f"Pushed data for {len(latest_data)} devices")
            else:
                logger.debug("No data to push")
            
        except Exception as e:
            logger.error(f"Error in background thread: {e}")
        
        time.sleep(30)  # Update setiap 30 detik

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db_manager.get_system_status()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected'
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
    
    logger.info("Starting PZEM Dashboard Server...")
    
    # Run the application
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5000, 
        debug=False,  # Set to False in production
        use_reloader=False  # Disable reloader to prevent thread duplication
    )
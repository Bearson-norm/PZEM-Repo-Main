#!/usr/bin/env python3
"""
Windows Compatible Flask Dashboard untuk PZEM - Tanpa emoji
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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*", logger=False)

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
        """Ambil status sistem keseluruhan"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Total devices
            cursor.execute("SELECT COUNT(DISTINCT device_address) as total FROM pzem_data")
            total_devices = cursor.fetchone()['total'] or 0
            
            # Online devices (data dalam 10 menit terakhir)
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
                        device_address, power, energy, created_at
                    FROM pzem_data 
                    ORDER BY device_address, created_at DESC
                )
                SELECT 
                    COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '10 minutes' 
                                 THEN COALESCE(power, 0) ELSE 0 END), 0) as total_power,
                    COALESCE(SUM(COALESCE(energy, 0)), 0) as total_energy
                FROM latest_data
            """)
            
            totals = cursor.fetchone()
            total_power = round(float(totals['total_power'] or 0), 2)
            total_energy = round(float(totals['total_energy'] or 0), 2)
            
            cursor.close()
            
            return {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'total_power': total_power,
                'total_energy': total_energy
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting system status: {e}")
            return {
                'total_devices': 0,
                'online_devices': 0,
                'total_power': 0,
                'total_energy': 0
            }
    
    def get_devices(self):
        """Ambil daftar semua device"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
            SELECT 
                d.device_address,
                COALESCE(dm.device_name, 'Device ' || d.device_address) as device_name,
                COALESCE(dm.location, 'Unknown') as location,
                COUNT(d.id) as data_count,
                MAX(d.created_at) as last_seen,
                AVG(d.power) as avg_power,
                AVG(d.voltage) as avg_voltage,
                AVG(d.current) as avg_current,
                MAX(d.energy) as total_energy,
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
        """Ambil data agregat untuk grafik"""
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
        """Ambil data terbaru dari semua device"""
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
                created_at
            FROM pzem_data 
            ORDER BY device_address, created_at DESC
            """
            
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            
            logger.debug(f"[DATABASE] Retrieved {len(data)} devices from database")
            
            # Convert to dictionary with device_address as key and serialize
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
        logger.error(f"[ERROR] Error in system status API: {e}")
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
    """API untuk data grafik device"""
    try:
        period = request.args.get('period', 'hour')
        data = db_manager.get_aggregated_data(device_address, period)
        return jsonify(data)
    except Exception as e:
        logger.error(f"[ERROR] Error in chart data API: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/all-latest')
def api_all_latest():
    """API untuk mendapatkan data terbaru semua device"""
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

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('[WEBSOCKET] Client connected')
    emit('connected', {'data': 'Connected to PZEM Dashboard'})
    
    # Send initial data
    try:
        latest_data = db_manager.get_all_latest_data()
        emit('data_update', latest_data)
        logger.debug(f"[WEBSOCKET] Sent initial data for {len(latest_data)} devices")
    except Exception as e:
        logger.error(f"[ERROR] Error sending initial data: {e}")
        emit('data_update', {})

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

# Background task untuk push data realtime
def background_thread():
    """Background task yang mengirim data terbaru secara berkala"""
    logger.info("[BACKGROUND] Starting background data push thread")
    
    while True:
        try:
            logger.debug("[BACKGROUND] Fetching latest data from database...")
            latest_data = db_manager.get_all_latest_data()
            
            if latest_data:
                logger.debug(f"[BACKGROUND] Retrieved data for {len(latest_data)} devices")
                
                # Test JSON serialization
                try:
                    json_test = json.dumps(latest_data)
                    logger.debug(f"[BACKGROUND] JSON serialization test passed ({len(json_test)} chars)")
                except Exception as json_error:
                    logger.error(f"[ERROR] JSON serialization test failed: {json_error}")
                    socketio.emit('data_update', {})
                    continue
                
                # Emit data
                socketio.emit('data_update', latest_data)
                logger.debug(f"[BACKGROUND] Successfully pushed data for {len(latest_data)} devices")
                
            else:
                logger.debug("[BACKGROUND] No data to push, emitting empty dict")
                socketio.emit('data_update', {})
            
        except Exception as e:
            logger.error(f"[ERROR] Error in background thread: {e}")
            try:
                socketio.emit('data_update', {})
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
            'database': 'connected',
            'version': '2.0-windows-compatible'
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
    
    logger.info("[STARTING] PZEM Dashboard Server (Windows Compatible)")
    logger.info("[WEBSOCKET] Listening for connections on port 5000")
    logger.info("[DATABASE] Using improved database structure")
    
    # Run the application
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5000, 
        debug=False,
        use_reloader=False
    )
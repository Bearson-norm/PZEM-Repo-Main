#!/usr/bin/env python3
"""
Enhanced Flask Dashboard untuk monitoring data sensor PZEM secara realtime
Versi yang diperbaiki dengan API yang lebih komprehensif
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, timedelta
import threading
import time
from collections import defaultdict
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Setup logging
logging.basicConfig(level=logging.INFO)
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
        try:
            if self.connection is None or self.connection.closed:
                self.connect()
            # Test connection
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
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
            
            # Total power dari data terbaru setiap device
            cursor.execute("""
                WITH latest_data AS (
                    SELECT DISTINCT ON (device_address) 
                        device_address, 
                        COALESCE(current_active_power, avg_power, 0) as power,
                        COALESCE(current_active_energy, total_energy, 0) as energy
                    FROM pzem_data 
                    ORDER BY device_address, created_at DESC
                )
                SELECT 
                    COALESCE(SUM(power), 0) as total_power,
                    COALESCE(SUM(energy), 0) as total_energy
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
    
    def get_latest_data(self, limit=100):
        """Ambil data terbaru"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
            SELECT * FROM pzem_data 
            ORDER BY created_at DESC 
            LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            data = cursor.fetchall()
            cursor.close()
            
            return [dict(row) for row in data]
            
        except Exception as e:
            logger.error(f"Error getting latest data: {e}")
            return []
    
    def get_devices(self):
        """Ambil daftar semua device"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT DISTINCT device_address, 
                   COUNT(*) as data_count,
                   MAX(created_at) as last_seen
            FROM pzem_data 
            GROUP BY device_address
            ORDER BY device_address
            """
            
            cursor.execute(query)
            devices = cursor.fetchall()
            cursor.close()
            
            return devices
            
        except Exception as e:
            logger.error(f"Error getting devices: {e}")
            return []
    
    def get_device_data(self, device_address, period='hour', limit=50):
        """Ambil data device berdasarkan periode"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Tentukan interval berdasarkan periode
            if period == 'hour':
                interval = "1 hour"
            elif period == 'day':
                interval = "1 day"
            elif period == 'week':
                interval = "1 week"
            elif period == 'month':
                interval = "1 month"
            else:
                interval = "1 hour"
            
            query = f"""
            SELECT * FROM pzem_data 
            WHERE device_address = %s 
            AND created_at >= NOW() - INTERVAL '{interval}'
            ORDER BY created_at DESC
            LIMIT %s
            """
            
            cursor.execute(query, (device_address, limit))
            data = cursor.fetchall()
            cursor.close()
            
            return [dict(row) for row in data]
            
        except Exception as e:
            logger.error(f"Error getting device data: {e}")
            return []
    
    def get_aggregated_data(self, device_address, period='hour'):
        """Ambil data agregat untuk grafik"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Tentukan grouping berdasarkan periode
            if period == 'hour':
                date_trunc = "minute"
                interval = "1 hour"
                group_minutes = 5  # Group by 5 minutes
            elif period == 'day':
                date_trunc = "hour"
                interval = "1 day"
                group_minutes = 60  # Group by hour
            elif period == 'week':
                date_trunc = "day"
                interval = "1 week"
                group_minutes = 1440  # Group by day
            elif period == 'month':
                date_trunc = "day"
                interval = "1 month"
                group_minutes = 1440  # Group by day
            else:
                date_trunc = "minute"
                interval = "1 hour"
                group_minutes = 5
            
            if period == 'hour':
                # For hour period, group by 5-minute intervals
                query = f"""
                WITH time_groups AS (
                    SELECT 
                        EXTRACT(EPOCH FROM created_at)::INTEGER / (5 * 60) * (5 * 60) AS time_bucket,
                        AVG(COALESCE(current_voltage, avg_voltage, 0)) as voltage,
                        AVG(COALESCE(current_current, avg_current, 0)) as current,
                        AVG(COALESCE(current_active_power, avg_power, 0)) as power,
                        SUM(COALESCE(current_active_energy, total_energy, 0)) as energy
                    FROM pzem_data 
                    WHERE device_address = %s 
                    AND created_at >= NOW() - INTERVAL '{interval}'
                    GROUP BY time_bucket
                )
                SELECT 
                    TO_TIMESTAMP(time_bucket) as time_period,
                    voltage,
                    current,
                    power,
                    energy
                FROM time_groups
                ORDER BY time_bucket
                """
            else:
                query = f"""
                SELECT 
                    DATE_TRUNC('{date_trunc}', created_at) as time_period,
                    AVG(COALESCE(current_voltage, avg_voltage, 0)) as voltage,
                    AVG(COALESCE(current_current, avg_current, 0)) as current,
                    AVG(COALESCE(current_active_power, avg_power, 0)) as power,
                    SUM(COALESCE(current_active_energy, total_energy, 0)) as energy
                FROM pzem_data 
                WHERE device_address = %s 
                AND created_at >= NOW() - INTERVAL '{interval}'
                GROUP BY time_period
                ORDER BY time_period
                """
            
            cursor.execute(query, (device_address,))
            data = cursor.fetchall()
            cursor.close()
            
            return [dict(row) for row in data]
            
        except Exception as e:
            logger.error(f"Error getting aggregated data: {e}")
            return []
    
    def get_all_devices_latest_data(self):
        """Ambil data terbaru dari semua device"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
            SELECT DISTINCT ON (device_address) *
            FROM pzem_data 
            ORDER BY device_address, created_at DESC
            """
            
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            
            result = {}
            for row in data:
                result[row['device_address']] = dict(row)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting all devices latest data: {e}")
            return {}

# Inisialisasi database manager
db_manager = DatabaseManager()

# Routes
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/system-status')
def api_system_status():
    """API untuk status sistem keseluruhan"""
    try:
        status = db_manager.get_system_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error in system status API: {e}")
        return jsonify({
            'total_devices': 0,
            'online_devices': 0,
            'total_power': 0,
            'total_energy': 0
        })

@app.route('/api/devices')
def api_devices():
    """API untuk daftar semua device"""
    try:
        devices = db_manager.get_devices()
        return jsonify(devices)
    except Exception as e:
        logger.error(f"Error in devices API: {e}")
        return jsonify([])

@app.route('/api/latest/<device_address>')
def api_latest_data(device_address):
    """API untuk data terbaru device tertentu"""
    try:
        data = db_manager.get_device_data(device_address, 'hour', 1)
        return jsonify(data[0] if data else {})
    except Exception as e:
        logger.error(f"Error in latest data API: {e}")
        return jsonify({})

@app.route('/api/data/<device_address>')
def api_device_data(device_address):
    """API untuk data device berdasarkan periode"""
    try:
        period = request.args.get('period', 'hour')
        limit = int(request.args.get('limit', 50))
        data = db_manager.get_device_data(device_address, period, limit)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in device data API: {e}")
        return jsonify([])

@app.route('/api/chart/<device_address>')
def api_chart_data(device_address):
    """API untuk data chart device tertentu"""
    try:
        period = request.args.get('period', 'hour')
        data = db_manager.get_aggregated_data(device_address, period)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in chart data API: {e}")
        return jsonify([])

@app.route('/api/all-latest')
def api_all_latest():
    """API untuk mendapatkan data terbaru semua device"""
    try:
        latest_data = db_manager.get_all_devices_latest_data()
        return jsonify(latest_data)
    except Exception as e:
        logger.error(f"Error in all latest data API: {e}")
        return jsonify({})

@app.route('/api/combined-chart')
def api_combined_chart():
    """API untuk data chart gabungan semua device"""
    try:
        period = request.args.get('period', 'hour')
        devices = db_manager.get_devices()
        combined_data = {}
        
        for device in devices:
            device_address = device[0]
            data = db_manager.get_aggregated_data(device_address, period)
            combined_data[device_address] = data
        
        return jsonify(combined_data)
    except Exception as e:
        logger.error(f"Error in combined chart API: {e}")
        return jsonify({})

# WebSocket events
@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('connected', {'data': 'Connected to PZEM Dashboard'})

@socketio.on('disconnect')  
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('request_data')
def handle_request_data(data):
    """Handle request untuk data spesifik dari client"""
    try:
        request_type = data.get('type', 'latest')
        
        if request_type == 'system_status':
            status = db_manager.get_system_status()
            emit('system_status_update', status)
        elif request_type == 'all_latest':
            latest_data = db_manager.get_all_devices_latest_data()
            emit('data_update', latest_data)
        elif request_type == 'devices':
            devices = db_manager.get_devices()
            emit('devices_update', devices)
            
    except Exception as e:
        logger.error(f"Error handling data request: {e}")
        emit('error', {'message': 'Error fetching data'})

# Background task untuk push data realtime
def background_thread():
    """Background task yang mengirim data terbaru setiap 30 detik"""
    while True:
        try:
            # Ambil data terbaru semua device
            latest_data = db_manager.get_all_devices_latest_data()
            system_status = db_manager.get_system_status()
            
            # Emit ke semua client
            socketio.emit('data_update', latest_data)
            socketio.emit('system_status_update', system_status)
            
            logger.info(f"Broadcasting data update for {len(latest_data)} devices")
            
        except Exception as e:
            logger.error(f"Error in background thread: {e}")
        
        time.sleep(30)  # Update setiap 30 detik

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'disconnected',
            'error': str(e)
        }), 503

if __name__ == '__main__':
    logger.info("Starting PZEM Dashboard Server...")
    
    # Start background thread
    thread = threading.Thread(target=background_thread)
    thread.daemon = True
    thread.start()
    
    # Start Flask-SocketIO server
    socketio.run(app, 
                host='0.0.0.0', 
                port=5000, 
                debug=False,  # Set to False for production
                allow_unsafe_werkzeug=True)
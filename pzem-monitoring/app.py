#!/usr/bin/env python3
"""
Flask Dashboard untuk monitoring data sensor PZEM secara realtime
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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*")

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
        except Exception as e:
            print(f"Database connection error: {e}")
    
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
            
            # Total power dari data terbaru setiap device
            cursor.execute("""
                WITH latest_data AS (
                    SELECT DISTINCT ON (device_address) 
                        device_address, avg_power, total_energy
                    FROM pzem_data 
                    ORDER BY device_address, created_at DESC
                )
                SELECT 
                    COALESCE(SUM(avg_power), 0) as total_power,
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
            print(f"Error getting system status: {e}")
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
            print(f"Error getting latest data: {e}")
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
            print(f"Error getting devices: {e}")
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
            print(f"Error getting device data: {e}")
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
            elif period == 'day':
                date_trunc = "hour"
                interval = "1 day"
            elif period == 'week':
                date_trunc = "day"
                interval = "1 week"
            elif period == 'month':
                date_trunc = "day"
                interval = "1 month"
            else:
                date_trunc = "minute"
                interval = "1 hour"
            
            query = f"""
            SELECT 
                DATE_TRUNC('{date_trunc}', created_at) as time_period,
                AVG(avg_voltage) as voltage,
                AVG(avg_current) as current,
                AVG(avg_power) as power,
                SUM(total_energy) as energy
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
            print(f"Error getting aggregated data: {e}")
            return []

# Inisialisasi database manager
db_manager = DatabaseManager()

# Routes
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/system-status')
def api_system_status():
    """API untuk status sistem keseluruhan"""
    status = db_manager.get_system_status()
    return jsonify(status)

@app.route('/api/devices')
def api_devices():
    devices = db_manager.get_devices()
    return jsonify(devices)

@app.route('/api/latest/<device_address>')
def api_latest_data(device_address):
    data = db_manager.get_device_data(device_address, 'hour', 1)
    return jsonify(data[0] if data else {})

@app.route('/api/data/<device_address>')
def api_device_data(device_address):
    period = request.args.get('period', 'hour')
    data = db_manager.get_device_data(device_address, period)
    return jsonify(data)

@app.route('/api/chart/<device_address>')
def api_chart_data(device_address):
    period = request.args.get('period', 'hour')
    data = db_manager.get_aggregated_data(device_address, period)
    return jsonify(data)

@app.route('/api/all-latest')
def api_all_latest():
    """API untuk mendapatkan data terbaru semua device"""
    devices = db_manager.get_devices()
    latest_data = {}
    
    for device in devices:
        device_address = device[0]
        data = db_manager.get_device_data(device_address, 'hour', 1)
        if data:
            latest_data[device_address] = data[0]
    
    return jsonify(latest_data)

@app.route('/api/latest-data')
def api_latest_data():
    limit = request.args.get('limit', 100)
    data = db_manager.get_latest_data(int(limit))
    return jsonify(data)

@app.route('/api/all-chart')
def api_all_chart():
    period = request.args.get('period', 'hour')
    # Implementasi untuk mendapatkan data chart gabungan semua device
    devices = db_manager.get_devices()
    chart_data = []
    
    for device in devices:
        device_data = db_manager.get_aggregated_data(device[0], period)
        chart_data.extend(device_data)
    
    return jsonify(chart_data)

# WebSocket events
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'data': 'Connected to PZEM Dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

# Background task untuk push data realtime
def background_thread():
    """Background task yang mengirim data terbaru setiap 30 detik"""
    while True:
        try:
            # Ambil data terbaru semua device
            latest_data = {}
            devices = db_manager.get_devices()
            
            for device in devices:
                device_address = device[0]
                data = db_manager.get_device_data(device_address, 'hour', 1)
                if data:
                    latest_data[device_address] = data[0]
            
            # Emit ke semua client
            socketio.emit('data_update', latest_data)
            
        except Exception as e:
            print(f"Error in background thread: {e}")
        
        time.sleep(30)  # Update setiap 30 detik

# Mulai background thread
thread = threading.Thread(target=background_thread)
thread.daemon = True
thread.start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
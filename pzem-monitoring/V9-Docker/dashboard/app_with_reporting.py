#!/usr/bin/env python3
"""
PZEM 3-Phase Energy Monitoring Dashboard with Report Integration
Enhanced version with improved code structure and error handling
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
import os
from psycopg2.pool import SimpleConnectionPool
import pytz

# Timezone Jakarta
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# Import report modules
from report_routes import report_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*", logger=False)


# Register report blueprint
app.register_blueprint(report_bp)

# Setup logging with Windows compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'pzem_monitoring'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASS', 'Admin123')
}



class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')
        self.pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            **DB_CONFIG
        )
        self.connect()
        
        # Optimization: Simple in-memory cache with TTL
        self._cache = {}
        self._cache_ttl = {
            'system_status': 10,  # 10 seconds
            'devices': 30,  # 30 seconds
            'three_phase_summary': 15,  # 15 seconds
            'all_latest': 5  # 5 seconds (most frequently updated)
        }
    
    def _get_cache_key(self, key, *args):
        """Generate cache key"""
        return f"{key}_{hash(str(args))}"
    
    def _is_cache_valid(self, cache_key, ttl_seconds):
        """Check if cache entry is still valid"""
        if cache_key not in self._cache:
            return False
        
        cache_time, _ = self._cache[cache_key]
        age = (datetime.now() - cache_time).total_seconds()
        return age < ttl_seconds
    
    def _get_cached(self, cache_key):
        """Get value from cache if valid"""
        if cache_key in self._cache:
            _, value = self._cache[cache_key]
            return value
        return None
    
    def _set_cache(self, cache_key, value):
        """Store value in cache"""
        self._cache[cache_key] = (datetime.now(), value)
        
        # Clean old cache entries (keep only last 100 entries)
        if len(self._cache) > 100:
            # Remove oldest entries
            sorted_cache = sorted(self._cache.items(), key=lambda x: x[1][0])
            for key, _ in sorted_cache[:-100]:
                del self._cache[key]
    
    def get_jakarta_time(self):
        """Get current Jakarta time"""
        return datetime.now(self.jakarta_tz)
    
    def convert_to_jakarta(self, utc_datetime):
        """Convert UTC datetime to Jakarta timezone"""
        if utc_datetime is None:
            return None
        
        # If datetime is naive, assume it's UTC
        if utc_datetime.tzinfo is None:
            utc_datetime = pytz.UTC.localize(utc_datetime)
        
        # Convert to Jakarta timezone
        return utc_datetime.astimezone(self.jakarta_tz)

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
        """Status sistem dengan perhitungan online yang akurat (with caching)"""
        cache_key = self._get_cache_key('system_status')
        ttl = self._cache_ttl.get('system_status', 10)
        
        # Check cache first
        if self._is_cache_valid(cache_key, ttl):
            logger.debug("Returning cached system_status")
            return self._get_cached(cache_key)
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Total devices
            cursor.execute("SELECT COUNT(DISTINCT device_address) as total FROM pzem_data")
            total_devices = cursor.fetchone()['total'] or 0
            
            # Online devices dengan perhitungan yang akurat
            cursor.execute("""
                WITH latest_per_device AS (
                    SELECT DISTINCT ON (device_address) 
                        device_address, 
                        created_at,
                        COALESCE(power, 0) as power,
                        COALESCE(energy, 0) as energy
                    FROM pzem_data 
                    ORDER BY device_address, created_at DESC
                ),
                online_devices AS (
                    SELECT *,
                        CASE WHEN created_at >= NOW() - INTERVAL '10 minutes' 
                             THEN 1 ELSE 0 END as is_online
                    FROM latest_per_device
                )
                SELECT 
                    COUNT(*) as total_devices,
                    SUM(is_online) as online_devices,
                    SUM(CASE WHEN is_online = 1 THEN power ELSE 0 END) as total_power,
                    SUM(CASE WHEN is_online = 1 THEN energy ELSE 0 END) as total_energy
                FROM online_devices
            """)
            
            stats = cursor.fetchone()
            cursor.close()
            
            result = {
                'total_devices': int(stats['total_devices'] or 0),
                'online_devices': int(stats['online_devices'] or 0),
                'total_active_power': float(stats['total_power'] or 0),
                'total_energy': float(stats['total_energy'] or 0),
                'jakarta_time': datetime.now(self.jakarta_tz).isoformat(),
                'timezone': 'Asia/Jakarta'
            }
            
            # Cache the result
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            error_result = {
                'total_devices': 0,
                'online_devices': 0,
                'total_active_power': 0,
                'total_energy': 0,
                'jakarta_time': datetime.now(self.jakarta_tz).isoformat(),
                'timezone': 'Asia/Jakarta'
            }
            # Don't cache errors
            return error_result
    
    def get_devices(self):
        """Ambil daftar semua device dengan enhanced info – aman untuk banyak request paralel (with caching)"""
        cache_key = self._get_cache_key('devices')
        ttl = self._cache_ttl.get('devices', 30)
        
        # Check cache first
        if self._is_cache_valid(cache_key, ttl):
            logger.debug("Returning cached devices list")
            return self._get_cached(cache_key)
        
        conn = None
        try:
            conn = self.pool.getconn()   # ← ambil koneksi dari pool
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
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
            result = [self.serialize_data(dict(device)) for device in devices]
            
            # Cache the result
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"[ERROR] Error getting devices: {e}")
            return []
        finally:
            if conn:
                self.pool.putconn(conn)  # ← kembalikan koneksi ke pool
    
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
        """Data agregat dengan downsampling untuk performa yang lebih baik"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Konfigurasi dengan downsampling untuk performa
            period_configs = {
                'hour': {
                    'interval': '1 hour',
                    'group_by': "DATE_TRUNC('minute', created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')",
                    'max_points': 60  # 1 point per minute
                },
                'day': {
                    'interval': '1 day', 
                    'group_by': "DATE_TRUNC('15 minutes', created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')",
                    'max_points': 96  # 1 point per 15 minutes (24*4)
                },
                'week': {
                    'interval': '1 week',
                    'group_by': "DATE_TRUNC('hour', created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')", 
                    'max_points': 168  # 1 point per hour (7*24)
                },
                'month': {
                    'interval': '1 month',
                    'group_by': "DATE_TRUNC('6 hours', created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')",
                    'max_points': 120  # 1 point per 6 hours (30*4)
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
            
            # Downsampling tambahan jika masih terlalu banyak points
            if len(data) > config['max_points']:
                # Ambil sample setiap N points
                step = max(1, len(data) // config['max_points'])
                data = data[::step][:config['max_points']]
                logger.info(f"Downsampled {device_address} {period} data from {len(data)*step} to {len(data)} points")
            
            # Convert time periods untuk frontend
            result = []
            for row in data:
                row_dict = dict(row)
                if row_dict['time_period']:
                    # Time sudah dalam Jakarta timezone dari query
                    row_dict['time_period'] = row_dict['time_period'].isoformat()
                
                result.append(self.serialize_data(row_dict))
            
            logger.info(f"Returning {len(result)} aggregated data points for {device_address} ({period})")
            return result
            
        except Exception as e:
            logger.error(f"Error getting aggregated data: {e}")
            return []
    
    def get_all_latest_data(self):
        """Ambil data terbaru dengan timestamp yang benar - FIXED VERSION (with caching)"""
        cache_key = self._get_cache_key('all_latest')
        ttl = self._cache_ttl.get('all_latest', 5)
        
        # Check cache first (short TTL for latest data)
        if self._is_cache_valid(cache_key, ttl):
            logger.debug("Returning cached all_latest_data")
            return self._get_cached(cache_key)
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Query dengan konversi timezone yang benar
            query = """
            SELECT DISTINCT ON (device_address) 
                device_address,
                COALESCE(voltage, 0) as voltage,
                COALESCE(current, 0) as current,
                COALESCE(power, 0) as power,
                COALESCE(energy, 0) as energy,
                COALESCE(frequency, 50.0) as frequency,
                COALESCE(power_factor, 1.0) as power_factor,
                wifi_rssi,
                device_timestamp,
                device_status,
                data_quality,
                timestamp_utc,
                created_at,
                -- Konversi timezone untuk Jakarta
                created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta' as created_at_jakarta,
                CASE 
                    WHEN timestamp_utc IS NOT NULL 
                    THEN timestamp_utc AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta'
                    ELSE created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta'
                END as timestamp_jakarta,
                -- Hitung apakah device online (data dalam 10 menit terakhir)
                CASE 
                    WHEN created_at >= NOW() - INTERVAL '10 minutes' THEN true
                    ELSE false
                END as is_online,
                -- Hitung selisih waktu dalam menit
                EXTRACT(EPOCH FROM (NOW() - created_at))/60 as minutes_since_last_data
            FROM pzem_data 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY device_address, created_at DESC
            """
            
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            
            logger.info(f"Retrieved {len(data)} devices from database")
            
            result = {}
            for row in data:
                try:
                    device_data = dict(row)
                    device_address = row['device_address']
                    
                    # Format timestamps untuk frontend
                    if device_data['created_at_jakarta']:
                        device_data['created_at_jakarta'] = device_data['created_at_jakarta'].isoformat()
                    
                    if device_data['timestamp_jakarta']:
                        device_data['timestamp_jakarta'] = device_data['timestamp_jakarta'].isoformat()
                    
                    if device_data['created_at']:
                        device_data['created_at'] = device_data['created_at'].isoformat()
                    
                    if device_data['timestamp_utc']:
                        device_data['timestamp_utc'] = device_data['timestamp_utc'].isoformat()
                    
                    # Add alias fields for backward compatibility
                    device_data['avg_power'] = device_data['power']
                    device_data['avg_voltage'] = device_data['voltage']
                    device_data['avg_current'] = device_data['current']
                    device_data['total_energy'] = device_data['energy']
                    
                    # Status informasi
                    device_data['online_status'] = device_data['is_online']
                    device_data['last_seen_minutes'] = float(device_data['minutes_since_last_data'] or 0)
                    
                    # Serialize data
                    serialized_data = self.serialize_data(device_data)
                    result[device_address] = serialized_data
                    
                    logger.debug(f"Device {device_address}: online={device_data['is_online']}, last_seen={device_data['last_seen_minutes']:.1f}min ago")
                    
                except Exception as device_error:
                    logger.error(f"Error processing device {row.get('device_address', 'unknown')}: {device_error}")
                    continue
            
            logger.info(f"Final result contains {len(result)} devices")
            
            # Cache the result
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error getting all latest data: {e}")
            return {}

    def get_three_phase_summary(self):
        """Get 3-phase system summary for quick overview (with caching)"""
        cache_key = self._get_cache_key('three_phase_summary')
        ttl = self._cache_ttl.get('three_phase_summary', 15)
        
        # Check cache first
        if self._is_cache_valid(cache_key, ttl):
            logger.debug("Returning cached three_phase_summary")
            return self._get_cached(cache_key)
        
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
                
                result_data = {
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
                
                # Cache the result
                self._set_cache(cache_key, result_data)
                return result_data
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

# API Endpoints yang diperbaiki
@app.route('/api/system-status')
def api_system_status():
    """API sistem status dengan debugging"""
    try:
        status = db_manager.get_system_status()
        
        # Log untuk debugging
        logger.info(f"System status: {status['online_devices']}/{status['total_devices']} online, "
                   f"{status['total_active_power']}W total")
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error in system status API: {e}")
        return jsonify({
            'total_devices': 0,
            'online_devices': 0,
            'total_active_power': 0,
            'total_energy': 0,
            'error': str(e)
        }), 500

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
    """API chart data dengan debugging"""
    try:
        period = request.args.get('period', 'hour')
        data = db_manager.get_aggregated_data(device_address, period)
        
        logger.info(f"Chart data for {device_address} ({period}): {len(data)} points")
        
        # Log sample data untuk debugging
        if data:
            sample_point = data[0]
            logger.debug(f"Sample chart point: time_period={sample_point.get('time_period')}, "
                        f"power={sample_point.get('power')}")
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Error in chart data API: {e}")
        return jsonify([]), 500

@app.route('/api/debug/latest-raw')
def api_debug_latest_raw():
    """Debug endpoint untuk melihat raw data"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT DISTINCT ON (device_address) 
            device_address,
            voltage, current, power, energy,
            created_at,
            created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta' as jakarta_time,
            EXTRACT(EPOCH FROM (NOW() - created_at))/60 as minutes_ago,
            CASE WHEN created_at >= NOW() - INTERVAL '10 minutes' THEN 'ONLINE' ELSE 'OFFLINE' END as status
        FROM pzem_data 
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        ORDER BY device_address, created_at DESC
        LIMIT 10
        """
        
        cursor.execute(query)
        raw_data = cursor.fetchall()
        cursor.close()
        
        result = []
        for row in raw_data:
            row_dict = dict(row)
            # Convert datetime objects to strings
            if row_dict['created_at']:
                row_dict['created_at'] = row_dict['created_at'].isoformat()
            if row_dict['jakarta_time']:
                row_dict['jakarta_time'] = row_dict['jakarta_time'].isoformat()
            result.append(row_dict)
        
        return jsonify({
            'raw_data': result,
            'current_time_utc': datetime.utcnow().isoformat(),
            'current_time_jakarta': datetime.now(JAKARTA_TZ).isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/all-latest')
def api_all_latest():
    """API data terbaru dengan debugging"""
    try:
        data = db_manager.get_all_latest_data()
        
        # Debug informasi
        online_count = sum(1 for device in data.values() 
                          if device.get('is_online') or device.get('online_status'))
        
        logger.info(f"All latest API: {len(data)} devices, {online_count} online")
        
        # Log sample device untuk debugging
        if data:
            sample_device = next(iter(data.values()))
            logger.debug(f"Sample device data: created_at_jakarta={sample_device.get('created_at_jakarta')}, "
                        f"is_online={sample_device.get('is_online')}")
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Error in all latest API: {e}")
        return jsonify({}), 500

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
    """Background task dengan debugging yang lebih baik"""
    logger.info("[BACKGROUND] Starting enhanced background data push thread (Jakarta timezone)")
    
    while True:
        try:
            jakarta_now = datetime.now(JAKARTA_TZ)
            logger.debug(f"[BACKGROUND] Fetching data at {jakarta_now.strftime('%Y-%m-%d %H:%M:%S')} WIB")
            
            # Ambil data terbaru dengan timestamp yang sudah diperbaiki
            latest_data = db_manager.get_all_latest_data()
            three_phase_summary = db_manager.get_three_phase_summary() if hasattr(db_manager, 'get_three_phase_summary') else {}
            
            if latest_data or three_phase_summary:
                combined_data = {
                    'devices': latest_data,
                    'summary': three_phase_summary,
                    'timestamp': jakarta_now.isoformat(),
                    'timezone': 'Asia/Jakarta',
                    'server_time': jakarta_now.strftime('%H:%M:%S WIB')
                }
                
                # Debug informasi
                online_count = sum(1 for device in latest_data.values() 
                                 if device.get('is_online') or device.get('online_status'))
                
                logger.debug(f"[BACKGROUND] Retrieved data for {len(latest_data)} devices, {online_count} online")
                
                # Test JSON serialization sebelum emit
                try:
                    import json
                    json_test = json.dumps(combined_data, default=str)
                    logger.debug(f"[BACKGROUND] JSON test passed ({len(json_test)} chars)")
                except Exception as json_error:
                    logger.error(f"[ERROR] JSON serialization failed: {json_error}")
                    # Emit data kosong jika serialization gagal
                    socketio.emit('data_update', {
                        'devices': {}, 
                        'summary': {},
                        'timestamp': jakarta_now.isoformat(),
                        'error': 'serialization_failed'
                    })
                    continue
                
                # Emit data yang sudah diperbaiki
                socketio.emit('data_update', combined_data)
                logger.debug(f"[BACKGROUND] Successfully pushed data at {jakarta_now.strftime('%H:%M:%S')} WIB")
                
            else:
                logger.debug("[BACKGROUND] No data to push")
                socketio.emit('data_update', {
                    'devices': {}, 
                    'summary': {},
                    'timestamp': jakarta_now.isoformat(),
                    'timezone': 'Asia/Jakarta'
                })
            
        except Exception as e:
            logger.error(f"[ERROR] Error in background thread: {e}")
            try:
                error_time = datetime.now(JAKARTA_TZ)
                socketio.emit('data_update', {
                    'devices': {}, 
                    'summary': {},
                    'timestamp': error_time.isoformat(),
                    'timezone': 'Asia/Jakarta',
                    'error': str(e)
                })
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
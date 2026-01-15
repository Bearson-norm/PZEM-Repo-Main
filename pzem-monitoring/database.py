# database.py
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import json
import logging
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.pool = None
        self.init_pool()
        self.create_tables()
    
    def init_pool(self):
        """Initialize connection pool"""
        try:
            self.pool = SimpleConnectionPool(
                1, 20,
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Error initializing database pool: {e}")
            raise
    
    def get_connection(self):
        """Get connection from pool"""
        return self.pool.getconn()
    
    def put_connection(self, conn):
        """Return connection to pool"""
        self.pool.putconn(conn)
    
    def create_tables(self):
        """Create necessary tables"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Main sensor data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pzem_data (
                    id SERIAL PRIMARY KEY,
                    device_address VARCHAR(50) NOT NULL,
                    timestamp BIGINT NOT NULL,
                    wifi_rssi INTEGER,
                    interval_minutes INTEGER,
                    sample_count INTEGER,
                    period_start BIGINT,
                    period_end BIGINT,
                    avg_voltage DECIMAL(10,4),
                    avg_current DECIMAL(10,4),
                    avg_power DECIMAL(10,4),
                    total_energy DECIMAL(10,6),
                    min_voltage DECIMAL(10,4),
                    max_voltage DECIMAL(10,4),
                    min_current DECIMAL(10,4),
                    max_current DECIMAL(10,4),
                    min_power DECIMAL(10,4),
                    max_power DECIMAL(10,4),
                    current_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_device_timestamp (device_address, timestamp),
                    INDEX idx_created_at (created_at)
                )
            """)
            
            # Device status table for quick lookup
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_status (
                    device_address VARCHAR(50) PRIMARY KEY,
                    last_seen TIMESTAMP,
                    is_online BOOLEAN DEFAULT TRUE,
                    last_voltage DECIMAL(10,4),
                    last_current DECIMAL(10,4),
                    last_power DECIMAL(10,4),
                    last_energy DECIMAL(10,6),
                    wifi_rssi INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Database tables created successfully")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error creating tables: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self.put_connection(conn)
    
    def insert_sensor_data(self, data):
        """Insert sensor data into database"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Insert into main data table
            cursor.execute("""
                INSERT INTO pzem_data (
                    device_address, timestamp, wifi_rssi, interval_minutes,
                    sample_count, period_start, period_end, avg_voltage,
                    avg_current, avg_power, total_energy, min_voltage,
                    max_voltage, min_current, max_current, min_power,
                    max_power, current_data
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                data['device_address'], data['timestamp'], data['wifi_rssi'],
                data['interval_minutes'], data['sample_count'], data['period_start'],
                data['period_end'], data['avg_voltage'], data['avg_current'],
                data['avg_power'], data['total_energy'], data['min_voltage'],
                data['max_voltage'], data['min_current'], data['max_current'],
                data['min_power'], data['max_power'], json.dumps(data['current_data'])
            ))
            
            # Update device status
            cursor.execute("""
                INSERT INTO device_status (
                    device_address, last_seen, is_online, last_voltage,
                    last_current, last_power, last_energy, wifi_rssi
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (device_address) DO UPDATE SET
                    last_seen = EXCLUDED.last_seen,
                    is_online = EXCLUDED.is_online,
                    last_voltage = EXCLUDED.last_voltage,
                    last_current = EXCLUDED.last_current,
                    last_power = EXCLUDED.last_power,
                    last_energy = EXCLUDED.last_energy,
                    wifi_rssi = EXCLUDED.wifi_rssi,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                data['device_address'], datetime.now(), data['current_data']['enabled'],
                data['current_data']['voltage'], data['current_data']['current'],
                data['current_data']['active_power'], data['current_data']['active_energy'],
                data['wifi_rssi']
            ))
            
            conn.commit()
            logger.info(f"Data inserted for device {data['device_address']}")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error inserting data: {e}")
            return False
        finally:
            if conn:
                cursor.close()
                self.put_connection(conn)
    
    def get_devices(self):
        """Get all devices with their latest status"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM device_status 
                ORDER BY device_address
            """)
            
            devices = cursor.fetchall()
            return [dict(device) for device in devices]
            
        except Exception as e:
            logger.error(f"Error getting devices: {e}")
            return []
        finally:
            if conn:
                cursor.close()
                self.put_connection(conn)
    
    def get_device_data(self, device_address, period='hour', limit=100):
        """Get historical data for a device"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Calculate time range based on period
            now = datetime.now()
            if period == 'hour':
                start_time = now - timedelta(hours=1)
            elif period == 'day':
                start_time = now - timedelta(days=1)
            elif period == 'week':
                start_time = now - timedelta(weeks=1)
            elif period == 'month':
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(hours=1)
            
            if device_address == 'all':
                cursor.execute("""
                    SELECT * FROM pzem_data 
                    WHERE created_at >= %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (start_time, limit))
            else:
                cursor.execute("""
                    SELECT * FROM pzem_data 
                    WHERE device_address = %s AND created_at >= %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (device_address, start_time, limit))
            
            data = cursor.fetchall()
            return [dict(row) for row in data]
            
        except Exception as e:
            logger.error(f"Error getting device data: {e}")
            return []
        finally:
            if conn:
                cursor.close()
                self.put_connection(conn)
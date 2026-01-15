#!/usr/bin/env python3
"""
PZEM MQTT Client for Energy Monitoring
Enhanced Windows-compatible version with improved error handling
"""

import json
import paho.mqtt.client as mqtt
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
import time
import sys
import signal
import os
import pytz

# Jakarta timezone for local time handling
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# MQTT Configuration
MQTT_BROKER = "103.87.67.139"
MQTT_PORT = 1883
MQTT_TOPIC = "energy/pzem/data"  # Only listen to data topic
MQTT_QOS = 1

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'pzem_monitoring'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASS', 'Admin123')
}

# Setup logging with Windows compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mqtt_client.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class PZEMDataHandler:
    def __init__(self):
        self.db_connection = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')
        self.connect_db()
        
    def connect_db(self):
        """Koneksi ke PostgreSQL dengan retry logic"""
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                self.db_connection = psycopg2.connect(**DB_CONFIG)
                self.reconnect_attempts = 0  # Reset counter
                logger.info("Connected to PostgreSQL database")
                return
            except Exception as e:
                self.reconnect_attempts += 1
                logger.error(f"Database connection attempt {self.reconnect_attempts} failed: {e}")
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    time.sleep(5)  # Wait 5 seconds before retry
                else:
                    logger.error("Max reconnection attempts reached. Exiting.")
                    sys.exit(1)
    
    def ensure_db_connection(self):
        """Pastikan koneksi database aktif"""
        try:
            if self.db_connection is None or self.db_connection.closed:
                logger.warning("Database connection lost, reconnecting...")
                self.connect_db()
            else:
                # Test connection
                cursor = self.db_connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            self.connect_db()
    
    def create_tables(self):
        """Pastikan tabel ada dengan struktur yang benar"""
        try:
            self.ensure_db_connection()
            cursor = self.db_connection.cursor()
            
            # Create table jika belum ada (struktur sudah dibuat di fresh_setup)
            create_table_query = """
            CREATE TABLE IF NOT EXISTS pzem_data (
                id SERIAL PRIMARY KEY,
                device_address VARCHAR(20) NOT NULL,
                voltage DECIMAL(8,2),
                current DECIMAL(8,3),
                power DECIMAL(10,2),
                energy DECIMAL(12,3),
                frequency DECIMAL(6,2) DEFAULT 50.0,
                power_factor DECIMAL(5,3) DEFAULT 1.0,
                wifi_rssi INTEGER,
                device_timestamp BIGINT,
                sample_interval INTEGER DEFAULT 60,
                sample_count INTEGER DEFAULT 1,
                device_status VARCHAR(20) DEFAULT 'online',
                data_quality VARCHAR(20) DEFAULT 'good',
                timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS pzem_devices (
                device_address VARCHAR(20) PRIMARY KEY,
                device_name VARCHAR(100),
                location VARCHAR(100),
                device_type VARCHAR(50) DEFAULT 'PZEM',
                installation_date DATE DEFAULT CURRENT_DATE,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                total_records INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Indexes jika belum ada
            CREATE INDEX IF NOT EXISTS idx_pzem_device_created ON pzem_data(device_address, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_pzem_created_desc ON pzem_data(created_at DESC);
            """
            
            cursor.execute(create_table_query)
            self.db_connection.commit()
            cursor.close()
            logger.info("Database tables verified/created")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            self.db_connection.rollback()
    
    def save_sensor_data(self, data):
        """Simpan data sensor dengan timestamp Jakarta"""
        try:
            self.ensure_db_connection()
            cursor = self.db_connection.cursor()
            
            # Get Jakarta time for logging
            jakarta_now = datetime.now(self.jakarta_tz)
            
            # Validasi data yang diperlukan
            if not data.get('device_address'):
                logger.error("Missing device_address in data")
                return False
            
            # Extract dan bersihkan data (sama seperti sebelumnya)
            device_address = str(data.get('device_address')).strip()
            voltage = self.safe_float(data.get('voltage') or data.get('avg_voltage'))
            current = self.safe_float(data.get('current') or data.get('avg_current'))
            power = self.safe_float(data.get('power') or data.get('avg_power'))
            energy = self.safe_float(data.get('energy') or data.get('total_energy'))
            frequency = self.safe_float(data.get('frequency', 50.0))
            power_factor = self.safe_float(data.get('power_factor', 1.0))
            
            # Data tambahan
            wifi_rssi = self.safe_int(data.get('wifi_rssi'))
            device_timestamp = self.safe_int(data.get('timestamp') or data.get('device_timestamp'))
            sample_interval = self.safe_int(data.get('interval_minutes', 60))
            sample_count = self.safe_int(data.get('sample_count', 1))
            
            # Insert data dengan timestamp UTC (database tetap menggunakan UTC)
            insert_query = """
            INSERT INTO pzem_data (
                device_address, voltage, current, power, energy, frequency, 
                power_factor, wifi_rssi, device_timestamp, sample_interval, 
                sample_count, device_status, data_quality
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            values = (
                device_address, voltage, current, power, energy, frequency,
                power_factor, wifi_rssi, device_timestamp, sample_interval,
                sample_count, 'online', 'live'
            )
            
            cursor.execute(insert_query, values)
            
            # Update device metadata
            self.update_device_metadata(device_address, cursor)
            
            self.db_connection.commit()
            cursor.close()
            
            logger.info(f"[OK] Data saved for device {device_address} at {jakarta_now.strftime('%H:%M:%S')} WIB - Power: {power}W, Voltage: {voltage}V")
            return True
            
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False
    
    def update_device_metadata(self, device_address, cursor):
        """Update metadata device"""
        try:
            upsert_query = """
            INSERT INTO pzem_devices (device_address, last_seen, total_records)
            VALUES (%s, CURRENT_TIMESTAMP, 1)
            ON CONFLICT (device_address) 
            DO UPDATE SET 
                last_seen = CURRENT_TIMESTAMP,
                total_records = pzem_devices.total_records + 1,
                updated_at = CURRENT_TIMESTAMP;
            """
            
            cursor.execute(upsert_query, (device_address,))
            
        except Exception as e:
            logger.error(f"Error updating device metadata: {e}")
    
    def safe_float(self, value):
        """Safely convert value to float"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def safe_int(self, value):
        """Safely convert value to int"""
        if value is None or value == '':
            return None
        try:
            return int(float(value))  # float first to handle "123.0"
        except (ValueError, TypeError):
            return None

class MQTTClient:
    def __init__(self, data_handler):
        self.data_handler = data_handler
        self.client = None
        self.connected = False
        self.message_count = 0
        self.last_message_time = None
        self.running = True
        
    def setup_client(self):
        """Setup MQTT client"""
        # Use VERSION2 to avoid deprecation warning
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=self.data_handler)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        
        # Set keepalive and other options
        self.client.keep_alive = 60
        
        # Enable logging
        self.client.enable_logger(logger)
        
    def on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback ketika koneksi berhasil/gagal"""
        if rc == 0:
            self.connected = True
            logger.info(f"[SUCCESS] Connected to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
            
            # Subscribe ke topic spesifik
            result = client.subscribe(MQTT_TOPIC, MQTT_QOS)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"[SUCCESS] Subscribed to topic: {MQTT_TOPIC} (QoS: {MQTT_QOS})")
            else:
                logger.error(f"[ERROR] Failed to subscribe to topic: {MQTT_TOPIC}")
        else:
            self.connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier", 
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            logger.error(f"[ERROR] Failed to connect to MQTT broker, return code {rc}")
            logger.error(f"Error: {error_messages.get(rc, 'Unknown error')}")

    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        """Callback ketika subscribe berhasil"""
        logger.info(f"[SUCCESS] Subscription confirmed (Message ID: {mid}, QoS: {granted_qos})")

    def on_message(self, client, userdata, msg):
        """Callback ketika menerima pesan"""
        try:
            self.message_count += 1
            self.last_message_time = datetime.now()
            
            # Log basic message info
            logger.info(f"[MESSAGE #{self.message_count}] Topic: {msg.topic}")
            
            # Decode message
            payload = msg.payload.decode('utf-8')
            logger.debug(f"[PAYLOAD] Size: {len(payload)} bytes")
            
            # Parse JSON
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as e:
                logger.error(f"[ERROR] JSON decode error: {e}")
                logger.error(f"[ERROR] Raw payload: {payload[:200]}...")
                return
            
            # Validate data structure
            if not isinstance(data, dict):
                logger.error(f"[ERROR] Expected JSON object, got {type(data)}")
                return
            
            # Log key data points
            device = data.get('device_address', 'Unknown')
            power = data.get('power') or data.get('avg_power', 0)
            voltage = data.get('voltage') or data.get('avg_voltage', 0)
            
            logger.info(f"[DATA] Device {device}: {power}W, {voltage}V")
            
            # Simpan ke database
            if userdata.save_sensor_data(data):
                logger.debug("[DATABASE] Data successfully saved")
            else:
                logger.warning("[DATABASE] Data save failed")
            
        except Exception as e:
            logger.error(f"[ERROR] Error processing message: {e}")

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        """Callback ketika terputus"""
        self.connected = False
        if rc != 0:
            logger.warning(f"[WARNING] Unexpected disconnection (code: {rc})")
        else:
            logger.info("[INFO] Disconnected from MQTT broker")
    
    def connect_and_loop(self):
        """Koneksi dan mulai loop dengan retry logic"""
        max_connect_attempts = 10
        connect_attempt = 0
        connect_delay = 5  # seconds
        
        # Retry initial connection
        while connect_attempt < max_connect_attempts and self.running:
            try:
                logger.info(f"[CONNECTING] MQTT broker {MQTT_BROKER}:{MQTT_PORT} (Attempt {connect_attempt + 1}/{max_connect_attempts})")
                logger.info(f"[LISTENING] Topic: {MQTT_TOPIC}")
                
                self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
                
                # Start loop
                self.client.loop_start()
                
                # Wait a bit to see if connection succeeds
                time.sleep(2)
                
                if self.connected:
                    logger.info("[SUCCESS] Connected to MQTT broker")
                    break
                else:
                    raise Exception("Connection not established")
                    
            except Exception as e:
                connect_attempt += 1
                logger.warning(f"[RETRY] Connection attempt {connect_attempt} failed: {e}")
                
                if connect_attempt < max_connect_attempts:
                    logger.info(f"[RETRY] Retrying in {connect_delay} seconds...")
                    time.sleep(connect_delay)
                    # Increase delay for next retry (exponential backoff)
                    connect_delay = min(connect_delay * 1.5, 30)
                else:
                    logger.error(f"[ERROR] Failed to connect after {max_connect_attempts} attempts")
                    logger.error("[ERROR] MQTT broker may be unreachable. Check network connectivity and broker status.")
                    logger.info("[INFO] Container will continue running and retry periodically...")
        
        # Status monitoring loop (only if we're still running)
        try:
            last_status_time = time.time()
            
            while self.running:
                current_time = time.time()
                
                # Print status setiap 60 detik
                if current_time - last_status_time > 60:
                    status = "Connected" if self.connected else "Disconnected"
                    logger.info(f"[STATUS] {status} | Messages received: {self.message_count}")
                    
                    if self.last_message_time:
                        time_since_last = datetime.now() - self.last_message_time
                        logger.info(f"[STATUS] Last message: {time_since_last.total_seconds():.0f} seconds ago")
                    
                    last_status_time = current_time
                
                # Reconnect jika terputus
                if not self.connected:
                    logger.warning("[RECONNECTING] Attempting to reconnect...")
                    try:
                        self.client.reconnect()
                        time.sleep(10)
                    except Exception as reconnect_error:
                        logger.warning(f"[RETRY] Reconnection failed: {reconnect_error}")
                        time.sleep(10)  # Wait before next retry
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("[SHUTDOWN] Received interrupt signal")
            self.running = False
        except Exception as e:
            logger.error(f"[ERROR] Loop error: {e}")
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()

# Global variables untuk signal handling
mqtt_client_instance = None

def signal_handler(signum, frame):
    """Handler untuk graceful shutdown"""
    logger.info("[SHUTDOWN] Received shutdown signal")
    global mqtt_client_instance
    if mqtt_client_instance:
        mqtt_client_instance.running = False
    sys.exit(0)

def main():
    logger.info("Starting PZEM MQTT Client (Windows Compatible)...")
    logger.info(f"Target MQTT Topic: {MQTT_TOPIC}")
    logger.info(f"Database: {DB_CONFIG['database']} on {DB_CONFIG['host']}")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Inisialisasi handler database
    try:
        data_handler = PZEMDataHandler()
        data_handler.create_tables()
        logger.info("[SUCCESS] Database initialized successfully")
    except Exception as e:
        logger.error(f"[ERROR] Database initialization failed: {e}")
        return
    
    # Setup MQTT client
    global mqtt_client_instance
    mqtt_client_instance = MQTTClient(data_handler)
    mqtt_client_instance.setup_client()
    
    # Connect and start processing
    mqtt_client_instance.connect_and_loop()

if __name__ == "__main__":
    main()
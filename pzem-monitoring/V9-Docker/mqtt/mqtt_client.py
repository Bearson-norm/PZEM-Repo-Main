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
MQTT_TOPICS = [
    "energy/3phase/+/phase/+/data",  # Pattern untuk 3-phase system: energy/3phase/{building}/phase/{R|S|T}/data
    "energy/pzem/data"  # Direct PZEM data topic
]
MQTT_QOS = 1

# Device address to building mapping
# device_address "1", "2", "3" -> CKPG1 with phases R, S, T respectively
DEVICE_BUILDING_MAP = {
    "1": {"building": "CKPG1", "phase": "R"},
    "2": {"building": "CKPG1", "phase": "S"},
    "3": {"building": "CKPG1", "phase": "T"}
}

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
    
    def save_sensor_data(self, data, building=None, phase=None):
        """Simpan data sensor dengan timestamp Jakarta"""
        try:
            self.ensure_db_connection()
            cursor = self.db_connection.cursor()
            
            # Get Jakarta time for logging
            jakarta_now = datetime.now(self.jakarta_tz)
            
            # Extract device_address dari berbagai sumber
            # Priority: device_address > device_id > pzem_address > address > building+phase
            device_address = None
            if data.get('device_address'):
                device_address = str(data.get('device_address')).strip()
            elif data.get('device_id'):
                device_address = str(data.get('device_id')).strip()
            elif data.get('pzem_address'):
                device_address = str(data.get('pzem_address')).strip()
            elif data.get('address'):
                device_address = str(data.get('address')).strip()
            elif building and phase:
                # Fallback: gunakan kombinasi building-phase sebagai device_address
                device_address = f"{building}-{phase}"
            
            if not device_address:
                logger.error("Missing device_address in data - cannot determine device identifier")
                logger.error(f"Available fields: {list(data.keys())}")
                return False
            
            # Check if device_address is in mapping (1, 2, 3 -> CKPG1)
            if device_address in DEVICE_BUILDING_MAP:
                mapping = DEVICE_BUILDING_MAP[device_address]
                # Override building and phase from mapping if not already set
                if not building:
                    building = mapping["building"]
                if not phase:
                    phase = mapping["phase"]
                logger.info(f"[MAPPING] Device {device_address} mapped to {building} Phase {phase}")
            
            # Extract dan bersihkan data
            device_address = str(device_address).strip()
            # Handle both direct values and aggregated values (from energy/pzem/data)
            # Check current_data nested object if available
            current_data = data.get('current_data', {}) if isinstance(data.get('current_data'), dict) else {}
            
            voltage = self.safe_float(
                data.get('voltage') or 
                data.get('avg_voltage') or 
                current_data.get('voltage')
            )
            current = self.safe_float(
                data.get('current') or 
                data.get('avg_current') or 
                current_data.get('current')
            )
            power = self.safe_float(
                data.get('power') or 
                data.get('avg_power') or 
                data.get('active_power') or 
                current_data.get('active_power')
            )
            energy = self.safe_float(
                data.get('energy') or 
                data.get('total_energy') or 
                data.get('active_energy') or 
                current_data.get('active_energy')
            )
            frequency = self.safe_float(
                data.get('frequency') or 
                current_data.get('frequency') or 
                50.0
            )
            power_factor = self.safe_float(
                data.get('power_factor') or 
                current_data.get('power_factor') or 
                1.0
            )
            
            # Data tambahan
            wifi_rssi = self.safe_int(data.get('wifi_rssi'))
            device_timestamp = self.safe_int(data.get('timestamp') or data.get('device_timestamp') or data.get('time'))
            sample_interval = self.safe_int(data.get('interval_minutes', 60))
            sample_count = self.safe_int(data.get('sample_count', 1))
            
            # Get building and phase from data or parameters
            building = building or data.get('building') or data.get('building_id')
            phase = phase or data.get('phase') or data.get('phase_id')
            
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
            
            # Update device metadata dengan building dan phase
            self.update_device_metadata(device_address, cursor, building, phase)
            
            self.db_connection.commit()
            cursor.close()
            
            logger.info(f"[OK] Data saved for device {device_address} ({building}/{phase}) at {jakarta_now.strftime('%H:%M:%S')} WIB - Power: {power}W, Voltage: {voltage}V")
            return True
            
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False
    
    def update_device_metadata(self, device_address, cursor, building=None, phase=None):
        """Update metadata device dengan building dan phase"""
        try:
            # Build device name from building and phase if available
            device_name = None
            if building and phase:
                device_name = f"Phase {phase} - {building}"
            elif phase:
                device_name = f"Phase {phase}"
            elif building:
                device_name = f"Device {building}"
            
            # Use building as location
            location = building if building else None
            
            upsert_query = """
            INSERT INTO pzem_devices (device_address, device_name, location, last_seen, total_records)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 1)
            ON CONFLICT (device_address) 
            DO UPDATE SET 
                device_name = COALESCE(EXCLUDED.device_name, pzem_devices.device_name),
                location = COALESCE(EXCLUDED.location, pzem_devices.location),
                last_seen = CURRENT_TIMESTAMP,
                total_records = pzem_devices.total_records + 1,
                updated_at = CURRENT_TIMESTAMP;
            """
            
            cursor.execute(upsert_query, (device_address, device_name, location))
            
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
            
            # Subscribe ke semua topics
            for topic in MQTT_TOPICS:
                result = client.subscribe(topic, MQTT_QOS)
                if result[0] == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"[SUCCESS] Subscribed to topic: {topic} (QoS: {MQTT_QOS})")
                else:
                    logger.error(f"[ERROR] Failed to subscribe to topic: {topic}")
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
            
            # Extract building and phase from topic
            building = None
            phase = None
            try:
                topic_parts = msg.topic.split('/')
                
                # Handle different topic formats
                if msg.topic.startswith('energy/3phase/'):
                    # Topic format: energy/3phase/{building}/phase/{R|S|T}/data
                    if len(topic_parts) >= 5:
                        building = topic_parts[2]  # building ID
                        phase = topic_parts[4].upper()  # R, S, or T
                        logger.debug(f"[TOPIC] Building: {building}, Phase: {phase}")
                elif msg.topic == 'energy/pzem/data':
                    # Direct PZEM data - building/phase will be determined from device_address mapping
                    logger.debug(f"[TOPIC] Direct PZEM data - will use device_address mapping")
                else:
                    logger.warning(f"[WARNING] Unknown topic format: {msg.topic}")
            except Exception as e:
                logger.warning(f"[WARNING] Could not parse topic structure: {e}")
            
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
            
            # Extract device_address early to check mapping
            device_address = data.get('device_address') or data.get('device_id') or data.get('pzem_address') or data.get('address')
            
            # Check device_address mapping for CKPG1 (1,2,3 -> CKPG1 R,S,T)
            if device_address and str(device_address).strip() in DEVICE_BUILDING_MAP:
                mapping = DEVICE_BUILDING_MAP[str(device_address).strip()]
                # Override building and phase from mapping
                building = mapping["building"]
                phase = mapping["phase"]
                logger.info(f"[MAPPING] Device {device_address} mapped to {building} Phase {phase}")
            
            # Add building and phase to data (from topic or from mapping)
            if building:
                data['building'] = building
            if phase:
                data['phase'] = phase
                data['phase_id'] = phase
            
            # Also check if building/phase already in JSON payload (prefer topic/mapping)
            if not data.get('building') and data.get('building_id'):
                data['building'] = data['building_id']
            if not data.get('phase') and data.get('phase_id'):
                data['phase'] = data['phase_id']
            
            # Log key data points
            device = device_address or 'Unknown'
            # Handle both direct and nested current_data
            power = data.get('power') or data.get('avg_power') or data.get('active_power')
            if not power and isinstance(data.get('current_data'), dict):
                power = data['current_data'].get('active_power')
            voltage = data.get('voltage') or data.get('avg_voltage')
            if not voltage and isinstance(data.get('current_data'), dict):
                voltage = data['current_data'].get('voltage')
            
            logger.info(f"[DATA] Device {device} ({building}/{phase}): {power or 0}W, {voltage or 0}V")
            logger.debug(f"[DEBUG] Available fields in data: {list(data.keys())}")
            
            # Simpan ke database
            if userdata.save_sensor_data(data, building, phase):
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
                logger.info(f"[LISTENING] Topics: {', '.join(MQTT_TOPICS)}")
                
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
    logger.info(f"Target MQTT Topics: {', '.join(MQTT_TOPICS)}")
    logger.info(f"Device Mapping: {DEVICE_BUILDING_MAP}")
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
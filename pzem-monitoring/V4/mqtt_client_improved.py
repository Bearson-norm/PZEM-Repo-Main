#!/usr/bin/env python3
"""
Improved MQTT Client untuk menerima data sensor PZEM dengan struktur yang lebih baik
Hanya menerima data dari topic energy/pzem/data
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

# Konfigurasi MQTT - Topic lebih spesifik
MQTT_BROKER = "103.87.67.139"
MQTT_PORT = 1883
MQTT_TOPIC = "energy/pzem/data"  # Hanya menerima topic data
MQTT_QOS = 1

# Database config
DB_CONFIG = {
    'host': 'localhost',
    'database': 'pzem_monitoring',
    'user': 'postgres',
    'password': 'Admin123'
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mqtt_client.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class PZEMDataHandler:
    def __init__(self):
        self.db_connection = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
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
        """Buat struktur tabel yang lebih sederhana dan konsisten"""
        try:
            self.ensure_db_connection()
            cursor = self.db_connection.cursor()
            
            # Drop existing table jika ada (opsional, untuk clean slate)
            # cursor.execute("DROP TABLE IF EXISTS pzem_data;")
            
            # Tabel utama dengan struktur yang disederhanakan
            create_table_query = """
            CREATE TABLE IF NOT EXISTS pzem_data (
                id SERIAL PRIMARY KEY,
                device_address VARCHAR(20) NOT NULL,
                timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Basic measurements
                voltage DECIMAL(8,2),
                current DECIMAL(8,3),
                power DECIMAL(10,2),
                energy DECIMAL(12,3),
                frequency DECIMAL(6,2),
                power_factor DECIMAL(5,3),
                
                -- Additional data
                wifi_rssi INTEGER,
                device_timestamp BIGINT,
                
                -- Sampling info
                sample_interval INTEGER DEFAULT 60,
                sample_count INTEGER DEFAULT 1,
                
                -- Status
                device_status VARCHAR(20) DEFAULT 'online',
                data_quality VARCHAR(20) DEFAULT 'good',
                
                -- Indexes
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Indexes untuk performance
            CREATE INDEX IF NOT EXISTS idx_device_timestamp ON pzem_data(device_address, timestamp_utc DESC);
            CREATE INDEX IF NOT EXISTS idx_device_created ON pzem_data(device_address, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON pzem_data(timestamp_utc DESC);
            CREATE INDEX IF NOT EXISTS idx_created_at ON pzem_data(created_at DESC);
            
            -- Tabel untuk device metadata (opsional)
            CREATE TABLE IF NOT EXISTS pzem_devices (
                device_address VARCHAR(20) PRIMARY KEY,
                device_name VARCHAR(100),
                location VARCHAR(100),
                installation_date DATE,
                last_seen TIMESTAMP,
                total_records INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            cursor.execute(create_table_query)
            self.db_connection.commit()
            cursor.close()
            logger.info("Database tables created/verified with new structure")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            if self.db_connection:
                self.db_connection.rollback()
    
    def update_device_metadata(self, device_address):
        """Update metadata device"""
        try:
            cursor = self.db_connection.cursor()
            
            # Insert atau update device metadata
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
            cursor.close()
            
        except Exception as e:
            logger.error(f"Error updating device metadata: {e}")
    
    def save_sensor_data(self, data):
        """Simpan data sensor ke database dengan struktur baru"""
        try:
            self.ensure_db_connection()
            cursor = self.db_connection.cursor()
            
            # Validasi data yang diperlukan
            if not data.get('device_address'):
                logger.error("Missing device_address in data")
                return False
            
            # Extract dan bersihkan data
            device_address = str(data.get('device_address')).strip()
            
            # Data utama dari sensor
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
            
            # Current data jika ada
            current_data = data.get('current_data', {})
            if current_data:
                voltage = voltage or self.safe_float(current_data.get('voltage'))
                current = current or self.safe_float(current_data.get('current'))
                power = power or self.safe_float(current_data.get('active_power'))
                frequency = frequency or self.safe_float(current_data.get('frequency'))
                power_factor = power_factor or self.safe_float(current_data.get('power_factor'))
            
            # Insert data
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
                device_address,
                voltage,
                current, 
                power,
                energy,
                frequency,
                power_factor,
                wifi_rssi,
                device_timestamp,
                sample_interval,
                sample_count,
                'online',
                'good'
            )
            
            cursor.execute(insert_query, values)
            
            # Update device metadata
            self.update_device_metadata(device_address)
            
            self.db_connection.commit()
            cursor.close()
            
            logger.info(f"✅ Data saved for device {device_address} - Power: {power}W, Voltage: {voltage}V")
            return True
            
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return False
    
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
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, userdata=self.data_handler)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        
        # Set keepalive and other options
        self.client.keep_alive = 60
        
        # Enable logging
        self.client.enable_logger(logger)
        
    def on_connect(self, client, userdata, flags, rc):
        """Callback ketika koneksi berhasil/gagal"""
        if rc == 0:
            self.connected = True
            logger.info(f"✅ Connected to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
            
            # Subscribe ke topic spesifik
            result = client.subscribe(MQTT_TOPIC, MQTT_QOS)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Subscribed to topic: {MQTT_TOPIC} (QoS: {MQTT_QOS})")
            else:
                logger.error(f"❌ Failed to subscribe to topic: {MQTT_TOPIC}")
        else:
            self.connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier", 
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            logger.error(f"❌ Failed to connect to MQTT broker, return code {rc}")
            logger.error(f"Error: {error_messages.get(rc, 'Unknown error')}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback ketika subscribe berhasil"""
        logger.info(f"✅ Subscription confirmed (Message ID: {mid}, QoS: {granted_qos})")

    def on_message(self, client, userdata, msg):
        """Callback ketika menerima pesan"""
        try:
            self.message_count += 1
            self.last_message_time = datetime.now()
            
            # Log basic message info
            logger.info(f"📨 Message #{self.message_count} from topic: {msg.topic}")
            
            # Decode message
            payload = msg.payload.decode('utf-8')
            logger.debug(f"📄 Raw payload ({len(payload)} bytes): {payload[:200]}...")
            
            # Parse JSON
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                logger.error(f"📄 Problematic payload: {payload}")
                return
            
            # Validate data structure
            if not isinstance(data, dict):
                logger.error(f"❌ Expected JSON object, got {type(data)}")
                return
            
            # Log key data points
            device = data.get('device_address', 'Unknown')
            power = data.get('power') or data.get('avg_power', 0)
            voltage = data.get('voltage') or data.get('avg_voltage', 0)
            
            logger.info(f"📊 Device {device}: {power}W, {voltage}V")
            
            # Simpan ke database
            if userdata.save_sensor_data(data):
                logger.debug("✅ Data successfully saved to database")
            else:
                logger.warning("⚠️  Data save failed")
            
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            logger.error(f"📄 Message topic: {msg.topic}")
            logger.error(f"📄 Message payload: {msg.payload}")

    def on_disconnect(self, client, userdata, rc):
        """Callback ketika terputus"""
        self.connected = False
        if rc != 0:
            logger.warning(f"⚠️  Unexpected disconnection (code: {rc})")
        else:
            logger.info("👋 Disconnected from MQTT broker")
    
    def connect_and_loop(self):
        """Koneksi dan mulai loop"""
        try:
            logger.info(f"🔌 Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
            logger.info(f"📡 Listening for topic: {MQTT_TOPIC}")
            
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            
            # Start loop
            self.client.loop_start()
            
            # Status monitoring loop
            last_status_time = time.time()
            
            while self.running:
                current_time = time.time()
                
                # Print status setiap 60 detik
                if current_time - last_status_time > 60:
                    status = "🟢 Connected" if self.connected else "🔴 Disconnected"
                    logger.info(f"📊 Status: {status} | Messages received: {self.message_count}")
                    
                    if self.last_message_time:
                        time_since_last = datetime.now() - self.last_message_time
                        logger.info(f"⏰ Last message: {time_since_last.total_seconds():.0f} seconds ago")
                    
                    last_status_time = current_time
                
                # Reconnect jika terputus
                if not self.connected:
                    logger.warning("🔄 Attempting to reconnect...")
                    try:
                        self.client.reconnect()
                        time.sleep(10)
                    except:
                        pass
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("👋 Shutting down...")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()

# Global variables untuk signal handling
mqtt_client_instance = None

def signal_handler(signum, frame):
    """Handler untuk graceful shutdown"""
    logger.info("📡 Received shutdown signal")
    global mqtt_client_instance
    if mqtt_client_instance:
        mqtt_client_instance.running = False
    sys.exit(0)

def main():
    logger.info("🚀 Starting Improved PZEM MQTT Client...")
    logger.info(f"📡 Target MQTT Topic: {MQTT_TOPIC}")
    logger.info(f"🗄️  Database: {DB_CONFIG['database']} on {DB_CONFIG['host']}")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Inisialisasi handler database
    try:
        data_handler = PZEMDataHandler()
        data_handler.create_tables()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return
    
    # Setup MQTT client
    global mqtt_client_instance
    mqtt_client_instance = MQTTClient(data_handler)
    mqtt_client_instance.setup_client()
    
    # Connect and start processing
    mqtt_client_instance.connect_and_loop()

if __name__ == "__main__":
    main()
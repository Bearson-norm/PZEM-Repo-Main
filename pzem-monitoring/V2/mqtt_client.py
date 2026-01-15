#!/usr/bin/env python3
"""
MQTT Client untuk menerima data sensor PZEM dan menyimpan ke PostgreSQL
Versi yang diperbaiki dengan logging dan error handling yang lebih baik
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

# Konfigurasi
MQTT_BROKER = "103.87.67.139"
MQTT_PORT = 1883
MQTT_TOPIC = "energy/pzem/+"  # Subscribe ke semua device
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
        """Buat tabel jika belum ada"""
        try:
            self.ensure_db_connection()
            cursor = self.db_connection.cursor()
            
            # Tabel untuk data sensor
            create_table_query = """
            CREATE TABLE IF NOT EXISTS pzem_data (
                id SERIAL PRIMARY KEY,
                device_address VARCHAR(10) NOT NULL,
                timestamp_data BIGINT NOT NULL,
                wifi_rssi INTEGER,
                interval_minutes INTEGER,
                sample_count INTEGER,
                period_start BIGINT,
                period_end BIGINT,
                avg_voltage FLOAT,
                avg_current FLOAT,
                avg_power FLOAT,
                total_energy FLOAT,
                min_voltage FLOAT,
                max_voltage FLOAT,
                min_current FLOAT,
                max_current FLOAT,
                min_power FLOAT,
                max_power FLOAT,
                current_enabled BOOLEAN,
                current_address INTEGER,
                current_time_data BIGINT,
                current_frequency FLOAT,
                current_voltage FLOAT,
                current_current FLOAT,
                current_active_power FLOAT,
                current_reactive_power FLOAT,
                current_apparent_power FLOAT,
                current_power_factor FLOAT,
                current_active_energy FLOAT,
                current_resistance FLOAT,
                current_dimmed_voltage FLOAT,
                current_nominal_power FLOAT,
                current_thdi FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_pzem_device_timestamp ON pzem_data(device_address, timestamp_data);
            CREATE INDEX IF NOT EXISTS idx_pzem_created_at ON pzem_data(created_at);
            """
            
            cursor.execute(create_table_query)
            self.db_connection.commit()
            cursor.close()
            logger.info("Database tables created/verified")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            self.db_connection.rollback()
    
    def save_sensor_data(self, data):
        """Simpan data sensor ke database"""
        try:
            self.ensure_db_connection()
            cursor = self.db_connection.cursor()
            
            # Extract current_data
            current_data = data.get('current_data', {})
            
            insert_query = """
            INSERT INTO pzem_data (
                device_address, timestamp_data, wifi_rssi, interval_minutes,
                sample_count, period_start, period_end, avg_voltage,
                avg_current, avg_power, total_energy, min_voltage,
                max_voltage, min_current, max_current, min_power,
                max_power, current_enabled, current_address, current_time_data,
                current_frequency, current_voltage, current_current,
                current_active_power, current_reactive_power,
                current_apparent_power, current_power_factor,
                current_active_energy, current_resistance,
                current_dimmed_voltage, current_nominal_power, current_thdi
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            values = (
                data.get('device_address'),
                data.get('timestamp'),
                data.get('wifi_rssi'),
                data.get('interval_minutes'),
                data.get('sample_count'),
                data.get('period_start'),
                data.get('period_end'),
                data.get('avg_voltage'),
                data.get('avg_current'),
                data.get('avg_power'),
                data.get('total_energy'),
                data.get('min_voltage'),
                data.get('max_voltage'),
                data.get('min_current'),
                data.get('max_current'),
                data.get('min_power'),
                data.get('max_power'),
                current_data.get('enabled'),
                current_data.get('address'),
                current_data.get('time'),
                current_data.get('frequency'),
                current_data.get('voltage'),
                current_data.get('current'),
                current_data.get('active_power'),
                current_data.get('reactive_power'),
                current_data.get('apparent_power'),
                current_data.get('power_factor'),
                current_data.get('active_energy'),
                current_data.get('resistance'),
                current_data.get('dimmed_voltage'),
                current_data.get('nominal_power'),
                current_data.get('thdi')
            )
            
            cursor.execute(insert_query, values)
            self.db_connection.commit()
            cursor.close()
            
            logger.info(f"Data saved for device {data.get('device_address')} - Power: {data.get('avg_power')}W")
            
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            if self.db_connection:
                self.db_connection.rollback()

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
            logger.info(f"Connected to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
            
            # Subscribe ke topic
            result = client.subscribe(MQTT_TOPIC, MQTT_QOS)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Subscribed to topic: {MQTT_TOPIC} (QoS: {MQTT_QOS})")
            else:
                logger.error(f"Failed to subscribe to topic: {MQTT_TOPIC}")
        else:
            self.connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier", 
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")
            logger.error(f"Error: {error_messages.get(rc, 'Unknown error')}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback ketika subscribe berhasil"""
        logger.info(f"Subscription confirmed (Message ID: {mid}, QoS: {granted_qos})")

    def on_message(self, client, userdata, msg):
        """Callback ketika menerima pesan"""
        try:
            self.message_count += 1
            self.last_message_time = datetime.now()
            
            # Decode message
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            
            logger.info(f"Message #{self.message_count} from topic {msg.topic}")
            logger.debug(f"Payload size: {len(payload)} bytes")
            
            # Log key data
            device = data.get('device_address', 'Unknown')
            power = data.get('avg_power', 0)
            voltage = data.get('avg_voltage', 0)
            logger.info(f"Device {device}: {power}W, {voltage}V")
            
            # Simpan ke database
            userdata.save_sensor_data(data)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.debug(f"Raw payload: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def on_disconnect(self, client, userdata, rc):
        """Callback ketika terputus"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection (code: {rc})")
        else:
            logger.info("Disconnected from MQTT broker")
    
    def connect_and_loop(self):
        """Koneksi dan mulai loop"""
        try:
            logger.info(f"Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            
            # Start loop
            self.client.loop_start()
            
            # Status monitoring loop
            last_status_time = time.time()
            
            while self.running:
                current_time = time.time()
                
                # Print status setiap 60 detik
                if current_time - last_status_time > 60:
                    status = "Connected" if self.connected else "Disconnected"
                    logger.info(f"Status: {status} | Messages received: {self.message_count}")
                    
                    if self.last_message_time:
                        time_since_last = datetime.now() - self.last_message_time
                        logger.info(f"Last message: {time_since_last.total_seconds():.0f} seconds ago")
                    
                    last_status_time = current_time
                
                # Reconnect jika terputus
                if not self.connected:
                    logger.warning("Attempting to reconnect...")
                    try:
                        self.client.reconnect()
                        time.sleep(10)
                    except:
                        pass
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.running = False
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()

# Global variables untuk signal handling
mqtt_client_instance = None

def signal_handler(signum, frame):
    """Handler untuk graceful shutdown"""
    logger.info("Received shutdown signal")
    global mqtt_client_instance
    if mqtt_client_instance:
        mqtt_client_instance.running = False
    sys.exit(0)

def main():
    logger.info("Starting PZEM MQTT Client...")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Inisialisasi handler database
    data_handler = PZEMDataHandler()
    data_handler.create_tables()
    
    # Setup MQTT client
    global mqtt_client_instance
    mqtt_client_instance = MQTTClient(data_handler)
    mqtt_client_instance.setup_client()
    
    # Connect and start processing
    mqtt_client_instance.connect_and_loop()

if __name__ == "__main__":
    main()
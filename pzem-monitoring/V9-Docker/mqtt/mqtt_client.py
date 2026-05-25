#!/usr/bin/env python3
"""
PZEM MQTT Client for Energy Monitoring
Enhanced Windows-compatible version with improved error handling
"""

import sys
import os

_root = os.path.dirname(os.path.abspath(__file__))
for _parent in (_root, os.path.dirname(_root)):
    if os.path.isdir(os.path.join(_parent, "shared")):
        if _parent not in sys.path:
            sys.path.insert(0, _parent)
        break

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

from shared.pzem_ingest import (
    enrich_payload_from_topic,
    decode_json_payload,
    persist_pzem_reading,
    DEFAULT_DEVICE_BUILDING_MAP,
)

# Jakarta timezone for local time handling
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

# MQTT Configuration
MQTT_BROKER = "103.87.67.139"
MQTT_PORT = 1883
MQTT_TOPICS = [
    "energy/3phase/+/phase/+/data",   # Standard: energy/3phase/{site}/phase/{R|S|T}/data
    "energy/3phase/+/+/phase/+/data",  # Extended: energy/3phase/{parent}/{child}/phase/{R|S|T}/data
    "energy/pzem/data"  # Direct PZEM data topic
]
MQTT_QOS = 1

# Device address to building mapping (alias shared default)
DEVICE_BUILDING_MAP = DEFAULT_DEVICE_BUILDING_MAP

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

            CREATE TABLE IF NOT EXISTS mqtt_bridge_configs (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                broker_host VARCHAR(255) NOT NULL,
                broker_port INTEGER NOT NULL DEFAULT 1883,
                use_tls BOOLEAN NOT NULL DEFAULT FALSE,
                username VARCHAR(120),
                password_enc TEXT,
                topics JSONB NOT NULL DEFAULT '[]'::jsonb,
                qos SMALLINT NOT NULL DEFAULT 1,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                last_connect_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS canvas_definitions (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                type VARCHAR(50) NOT NULL,
                config JSONB NOT NULL DEFAULT '{}'::jsonb,
                poll_interval_seconds INTEGER DEFAULT 300,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS mqtt_bridge_config_id INTEGER
                REFERENCES mqtt_bridge_configs(id) ON DELETE SET NULL;
            CREATE INDEX IF NOT EXISTS idx_pzem_data_bridge_created
                ON pzem_data (mqtt_bridge_config_id, created_at DESC);
            """
            
            cursor.execute(create_table_query)
            self.db_connection.commit()
            cursor.close()
            logger.info("Database tables verified/created")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            self.db_connection.rollback()
    
    def save_sensor_data(self, data, building=None, phase=None, mqtt_bridge_config_id=None):
        """Simpan data sensor — delegasi ke shared.persist_pzem_reading."""
        try:
            self.ensure_db_connection()
            cursor = self.db_connection.cursor()
            jakarta_now = datetime.now(self.jakarta_tz)

            ok = persist_pzem_reading(
                cursor,
                data,
                building,
                phase,
                mqtt_bridge_config_id,
                DEVICE_BUILDING_MAP,
            )
            if not ok:
                logger.error("Missing device_address in data - cannot determine device identifier")
                logger.error("Available fields: %s", list(data.keys()))
                self.db_connection.rollback()
                cursor.close()
                return False

            self.db_connection.commit()
            cursor.close()

            da = str(data.get("device_address") or "").strip()
            logger.info(
                "[OK] Data saved for device %s at %s WIB",
                da,
                jakarta_now.strftime("%H:%M:%S"),
            )
            return True

        except Exception as e:
            logger.error("Error saving data: %s", e)
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
        # Use VERSION2 to avoid deprecation warning
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=self.data_handler)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        
        # Set keepalive and other options
        self.client.keep_alive = 60
        
        # Set connection timeout
        self.client.connect_timeout = 10
        
        # Enable automatic reconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)
        
        # Enable logging
        self.client.enable_logger(logger)
        
    def subscribe_to_topics(self, client):
        """Subscribe ke semua topics - dapat dipanggil dari on_connect atau reconnect"""
        for topic in MQTT_TOPICS:
            try:
                result = client.subscribe(topic, MQTT_QOS)
                if result[0] == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"[SUCCESS] Subscribed to topic: {topic} (QoS: {MQTT_QOS})")
                else:
                    logger.error(f"[ERROR] Failed to subscribe to topic: {topic}, error code: {result[0]}")
            except Exception as e:
                logger.error(f"[ERROR] Exception while subscribing to {topic}: {e}")

    def on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback ketika koneksi berhasil/gagal"""
        if rc == 0:
            self.connected = True
            logger.info(f"[SUCCESS] Connected to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
            
            # Subscribe ke semua topics
            self.subscribe_to_topics(client)
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
            
            jakarta_time = datetime.now(JAKARTA_TZ)
            logger.info(
                "[MESSAGE #%s] Topic: %s at %s WIB",
                self.message_count,
                msg.topic,
                jakarta_time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            
            data = decode_json_payload(msg.payload)
            if not data:
                return

            building, phase = enrich_payload_from_topic(data, msg.topic, DEVICE_BUILDING_MAP)

            if not msg.topic.startswith("energy/3phase/") and msg.topic != "energy/pzem/data":
                logger.warning("[WARNING] Unknown topic format: %s", msg.topic)

            device = data.get("device_address") or "Unknown"
            power = data.get("power") or data.get("avg_power") or data.get("active_power")
            if not power and isinstance(data.get("current_data"), dict):
                power = data["current_data"].get("active_power")
            voltage = data.get("voltage") or data.get("avg_voltage")
            if not voltage and isinstance(data.get("current_data"), dict):
                voltage = data["current_data"].get("voltage")

            logger.info(
                "[DATA] Device %s (%s/%s): %sW, %sV",
                device,
                building,
                phase,
                power or 0,
                voltage or 0,
            )

            if userdata.save_sensor_data(data, building, phase, mqtt_bridge_config_id=None):
                logger.debug("[DATABASE] Data successfully saved")
            else:
                logger.warning("[DATABASE] Data save failed")
            
        except json.JSONDecodeError as json_err:
            logger.error(f"[ERROR] JSON decode error in on_message: {json_err}")
            logger.error(f"[ERROR] Payload preview: {msg.payload[:200] if msg.payload else 'None'}...")
        except UnicodeDecodeError as unicode_err:
            logger.error(f"[ERROR] Unicode decode error: {unicode_err}")
            logger.error(f"[ERROR] Payload bytes: {msg.payload[:100] if msg.payload else 'None'}...")
        except Exception as e:
            logger.error(f"[ERROR] Error processing message: {e}")
            logger.error(f"[ERROR] Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")

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
                
                # Verify loop is running (check if thread exists and is alive)
                try:
                    if hasattr(self.client, '_thread'):
                        if not self.client._thread or not self.client._thread.is_alive():
                            logger.warning("[WARNING] MQTT loop thread not running, restarting...")
                            self.client.loop_stop()
                            time.sleep(1)
                            self.client.loop_start()
                except Exception as thread_check_err:
                    logger.debug(f"[DEBUG] Could not verify loop thread status: {thread_check_err}")
                
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
                    jakarta_now = datetime.now(JAKARTA_TZ)
                    logger.info(f"[STATUS] {status} | Messages received: {self.message_count} | Time: {jakarta_now.strftime('%Y-%m-%d %H:%M:%S')} WIB")
                    
                    if self.last_message_time:
                        time_since_last = datetime.now() - self.last_message_time
                        seconds_ago = time_since_last.total_seconds()
                        logger.info(f"[STATUS] Last message: {seconds_ago:.0f} seconds ago")
                        
                        # Warning jika tidak ada pesan dalam 5 menit
                        if seconds_ago > 300:
                            logger.warning(f"[WARNING] No messages received for {seconds_ago:.0f} seconds ({seconds_ago/60:.1f} minutes)")
                            logger.warning(f"[WARNING] Connection status: {self.connected}, checking connection health...")
                            
                            # Check if client is actually connected
                            try:
                                # Check connection status - is_connected() might not exist in all versions
                                if hasattr(self.client, 'is_connected'):
                                    is_conn = self.client.is_connected()
                                else:
                                    # Fallback: check if connected flag is set and socket exists
                                    is_conn = self.connected and hasattr(self.client, '_sock') and self.client._sock is not None
                                
                                if is_conn:
                                    logger.info("[INFO] MQTT client reports connected, but no messages received")
                                    logger.info("[INFO] This might indicate: 1) No messages published to subscribed topics, 2) Network issues, 3) Broker not forwarding messages")
                                else:
                                    logger.warning("[WARNING] MQTT client reports NOT connected")
                                    self.connected = False
                            except Exception as check_err:
                                logger.error(f"[ERROR] Error checking connection status: {check_err}")
                                # Assume disconnected if we can't check
                                self.connected = False
                    else:
                        logger.warning("[WARNING] No messages received yet")
                    
                    last_status_time = current_time
                
                # Reconnect jika terputus
                if not self.connected:
                    logger.warning("[RECONNECTING] Attempting to reconnect...")
                    try:
                        # Stop loop sebelum reconnect
                        self.client.loop_stop()
                        time.sleep(1)
                        
                        # Reconnect
                        self.client.reconnect()
                        
                        # Restart loop
                        self.client.loop_start()
                        
                        # Wait untuk connection dan subscription
                        time.sleep(3)
                        
                        # Pastikan subscribe ulang jika sudah connected
                        if self.connected:
                            logger.info("[RECONNECT] Reconnected successfully, resubscribing to topics...")
                            self.subscribe_to_topics(self.client)
                        else:
                            logger.warning("[RECONNECT] Reconnection attempt completed but not connected yet")
                            time.sleep(5)
                    except Exception as reconnect_error:
                        logger.warning(f"[RETRY] Reconnection failed: {reconnect_error}")
                        logger.warning(f"[RETRY] Error details: {type(reconnect_error).__name__}: {str(reconnect_error)}")
                        # Pastikan loop tetap berjalan
                        try:
                            if not self.client.loop_start.called:
                                self.client.loop_start()
                        except:
                            pass
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
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import paho.mqtt.client as mqtt
from datetime import datetime
import logging
import threading
import time
from typing import Dict, Any, Optional, List
import signal
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mqtt_energy_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MQTTEnergyDataParser:
    def __init__(self, mqtt_config: Dict[str, Any], db_config: Dict[str, str]):
        """
        Initialize MQTT Energy Data Parser
        
        Args:
            mqtt_config: Dictionary berisi konfigurasi MQTT broker
                        {'host': '103.87.67.139', 'port': 1883, 'topic': 'sensor/pzem/data'}
            db_config: Dictionary berisi konfigurasi database
                      {'host': 'localhost', 'database': 'pzem_monitoring', 'user': 'postgres', 'password': 'Admin123'}
        """
        self.mqtt_config = mqtt_config
        self.db_config = db_config
        self.connection = None
        self.mqtt_client = None
        self.is_running = False
        self.device_stats = {}  # Tracking statistik per device
        
        # Setup signal handlers untuk graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
        
    def connect_database(self) -> bool:
        """Membuat koneksi ke database PostgreSQL"""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            # Set autocommit untuk operasi individual
            self.connection.autocommit = False
            logger.info("Berhasil terhubung ke database PostgreSQL")
            return True
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            return False
    
    def create_tables(self):
        """Membuat tabel untuk menyimpan data energy monitoring"""
        create_main_table = """
        CREATE TABLE IF NOT EXISTS energy_data (
            id SERIAL PRIMARY KEY,
            device_address VARCHAR(50) NOT NULL,
            timestamp BIGINT NOT NULL,
            wifi_rssi INTEGER,
            interval_minutes INTEGER,
            sample_count INTEGER,
            period_start BIGINT,
            period_end BIGINT,
            avg_voltage DECIMAL(10,4),
            avg_current DECIMAL(10,5),
            avg_power DECIMAL(10,3),
            total_energy DECIMAL(10,4),
            min_voltage DECIMAL(10,1),
            max_voltage DECIMAL(10,1),
            min_current DECIMAL(10,3),
            max_current DECIMAL(10,3),
            min_power INTEGER,
            max_power DECIMAL(10,1),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(device_address, timestamp)
        );
        """
        
        create_current_data_table = """
        CREATE TABLE IF NOT EXISTS current_data (
            id SERIAL PRIMARY KEY,
            energy_data_id INTEGER REFERENCES energy_data(id) ON DELETE CASCADE,
            enabled BOOLEAN,
            address INTEGER,
            time BIGINT,
            frequency INTEGER,
            voltage DECIMAL(10,1),
            current DECIMAL(10,3),
            active_power DECIMAL(10,1),
            reactive_power DECIMAL(10,3),
            apparent_power DECIMAL(10,1),
            power_factor DECIMAL(5,3),
            active_energy DECIMAL(10,3),
            resistance DECIMAL(10,6),
            dimmed_voltage DECIMAL(10,4),
            nominal_power DECIMAL(10,2),
            thdi DECIMAL(10,6),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        create_device_stats_table = """
        CREATE TABLE IF NOT EXISTS device_statistics (
            id SERIAL PRIMARY KEY,
            device_address VARCHAR(50) NOT NULL,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_messages INTEGER DEFAULT 0,
            last_avg_power DECIMAL(10,3),
            last_total_energy DECIMAL(10,4),
            status VARCHAR(20) DEFAULT 'active',
            UNIQUE(device_address)
        );
        """
        
        # Index untuk performa yang lebih baik
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_energy_data_device_timestamp ON energy_data(device_address, timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_energy_data_timestamp ON energy_data(timestamp DESC);",
            "CREATE INDEX IF NOT EXISTS idx_current_data_energy_id ON current_data(energy_data_id);"
        ]
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(create_main_table)
                cursor.execute(create_current_data_table)
                cursor.execute(create_device_stats_table)
                
                for index_sql in create_indexes:
                    cursor.execute(index_sql)
                
                self.connection.commit()
                logger.info("Tabel dan index berhasil dibuat/sudah ada")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            self.connection.rollback()
    
    def setup_mqtt_client(self):
        """Setup MQTT client dan callback functions"""
        self.mqtt_client = mqtt.Client()
        
        # Callback functions
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_subscribe = self.on_subscribe
        
        # Set username/password jika diperlukan
        if 'username' in self.mqtt_config and 'password' in self.mqtt_config:
            self.mqtt_client.username_pw_set(
                self.mqtt_config['username'],
                self.mqtt_config['password']
            )
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback ketika berhasil connect ke MQTT broker"""
        if rc == 0:
            logger.info(f"Connected to MQTT broker {self.mqtt_config['host']}:{self.mqtt_config['port']}")
            # Subscribe ke topic
            topic = self.mqtt_config.get('topic', 'sensor/pzem/data')
            client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback ketika disconnect dari MQTT broker"""
        logger.warning(f"Disconnected from MQTT broker with result code {rc}")
    
    def on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback ketika berhasil subscribe"""
        logger.info(f"Subscription successful with QoS {granted_qos}")
    
    def on_message(self, client, userdata, msg):
        """Callback ketika menerima message dari MQTT"""
        try:
            # Decode message
            payload = msg.payload.decode('utf-8')
            topic = msg.topic
            
            logger.debug(f"Received message from topic {topic}: {payload[:100]}...")
            
            # Parse dan simpan data
            if self.parse_and_save_json(payload):
                # Update statistik device
                data = json.loads(payload)
                device_address = data.get('device_address')
                self.update_device_statistics(device_address, data)
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def parse_and_save_json(self, json_data: str) -> bool:
        """
        Parse JSON data dan simpan ke database
        
        Args:
            json_data: String JSON yang akan di-parse
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            # Parse JSON
            data = json.loads(json_data) if isinstance(json_data, str) else json_data
            device_address = data.get('device_address')
            
            # Insert ke tabel utama dengan handling duplicate
            main_insert_query = """
            INSERT INTO energy_data (
                device_address, timestamp, wifi_rssi, interval_minutes, sample_count,
                period_start, period_end, avg_voltage, avg_current, avg_power,
                total_energy, min_voltage, max_voltage, min_current, max_current,
                min_power, max_power
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) 
            ON CONFLICT (device_address, timestamp) 
            DO UPDATE SET
                wifi_rssi = EXCLUDED.wifi_rssi,
                avg_voltage = EXCLUDED.avg_voltage,
                avg_current = EXCLUDED.avg_current,
                avg_power = EXCLUDED.avg_power,
                total_energy = EXCLUDED.total_energy
            RETURNING id;
            """
            
            main_values = (
                device_address,
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
                data.get('max_power')
            )
            
            with self.connection.cursor() as cursor:
                cursor.execute(main_insert_query, main_values)
                result = cursor.fetchone()
                energy_data_id = result[0] if result else None
                
                # Insert current_data jika ada
                if energy_data_id and 'current_data' in data and data['current_data']:
                    # Delete existing current_data untuk update
                    cursor.execute("DELETE FROM current_data WHERE energy_data_id = %s", (energy_data_id,))
                    
                    current_data = data['current_data']
                    current_insert_query = """
                    INSERT INTO current_data (
                        energy_data_id, enabled, address, time, frequency, voltage,
                        current, active_power, reactive_power, apparent_power,
                        power_factor, active_energy, resistance, dimmed_voltage,
                        nominal_power, thdi
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );
                    """
                    
                    current_values = (
                        energy_data_id,
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
                    
                    cursor.execute(current_insert_query, current_values)
                
                self.connection.commit()
                logger.debug(f"Data dari device {device_address} berhasil disimpan dengan ID: {energy_data_id}")
                return True
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def update_device_statistics(self, device_address: str, data: dict):
        """Update statistik per device"""
        try:
            upsert_stats_query = """
            INSERT INTO device_statistics (device_address, last_seen, total_messages, last_avg_power, last_total_energy, status)
            VALUES (%s, CURRENT_TIMESTAMP, 1, %s, %s, 'active')
            ON CONFLICT (device_address)
            DO UPDATE SET
                last_seen = CURRENT_TIMESTAMP,
                total_messages = device_statistics.total_messages + 1,
                last_avg_power = EXCLUDED.last_avg_power,
                last_total_energy = EXCLUDED.last_total_energy,
                status = 'active';
            """
            
            with self.connection.cursor() as cursor:
                cursor.execute(upsert_stats_query, (
                    device_address,
                    data.get('avg_power'),
                    data.get('total_energy')
                ))
                self.connection.commit()
                
        except Exception as e:
            logger.error(f"Error updating device statistics: {e}")
            if self.connection:
                self.connection.rollback()
    
    def get_device_list(self) -> List[Dict]:
        """Mendapatkan daftar semua device yang aktif"""
        query = """
        SELECT 
            device_address,
            last_seen,
            total_messages,
            last_avg_power,
            last_total_energy,
            status
        FROM device_statistics
        ORDER BY last_seen DESC;
        """
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching device list: {e}")
            return []
    
    def get_device_data(self, device_address: str, limit: int = 100) -> List[Dict]:
        """
        Mendapatkan data untuk device tertentu
        
        Args:
            device_address: Alamat device yang akan diambil datanya
            limit: Jumlah data yang akan diambil
        """
        query = """
        SELECT 
            ed.*,
            cd.enabled, cd.frequency, cd.voltage as current_voltage,
            cd.current as current_current, cd.active_power as current_active_power,
            cd.power_factor, cd.active_energy
        FROM energy_data ed
        LEFT JOIN current_data cd ON ed.id = cd.energy_data_id
        WHERE ed.device_address = %s
        ORDER BY ed.timestamp DESC
        LIMIT %s;
        """
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (device_address, limit))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching data for device {device_address}: {e}")
            return []
    
    def get_all_recent_data(self, limit: int = 50) -> List[Dict]:
        """Mendapatkan data terbaru dari semua device"""
        query = """
        SELECT 
            ed.device_address,
            ed.timestamp,
            ed.avg_voltage,
            ed.avg_current,
            ed.avg_power,
            ed.total_energy,
            ed.wifi_rssi,
            cd.power_factor,
            ed.created_at
        FROM energy_data ed
        LEFT JOIN current_data cd ON ed.id = cd.energy_data_id
        ORDER BY ed.timestamp DESC
        LIMIT %s;
        """
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (limit,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching recent data: {e}")
            return []
    
    def start_monitoring(self):
        """Mulai monitoring MQTT"""
        if not self.connect_database():
            return False
        
        self.create_tables()
        self.setup_mqtt_client()
        
        try:
            # Connect ke MQTT broker
            self.mqtt_client.connect(
                self.mqtt_config['host'],
                self.mqtt_config.get('port', 1883),
                60  # keepalive
            )
            
            self.is_running = True
            logger.info("Starting MQTT monitoring...")
            
            # Start monitoring loop
            self.mqtt_client.loop_start()
            
            # Status reporting thread
            status_thread = threading.Thread(target=self.status_reporter, daemon=True)
            status_thread.start()
            
            # Keep main thread alive
            while self.is_running:
                time.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting MQTT monitoring: {e}")
            return False
    
    def status_reporter(self):
        """Thread untuk melaporkan status setiap 60 detik"""
        while self.is_running:
            try:
                time.sleep(60)  # Report setiap menit
                if self.is_running:
                    devices = self.get_device_list()
                    active_devices = [d for d in devices if d['status'] == 'active']
                    logger.info(f"Status: {len(active_devices)} active devices, "
                              f"total devices: {len(devices)}")
                    
                    # Log 5 device terakhir yang aktif
                    for device in active_devices[:5]:
                        logger.info(f"Device {device['device_address']}: "
                                  f"{device['total_messages']} messages, "
                                  f"last power: {device['last_avg_power']}W")
                        
            except Exception as e:
                logger.error(f"Error in status reporter: {e}")
    
    def stop(self):
        """Stop monitoring"""
        self.is_running = False
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT client disconnected")
        
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def close_connection(self):
        """Menutup koneksi database"""
        if self.connection:
            self.connection.close()
            logger.info("Koneksi database ditutup")

# Fungsi utility untuk monitoring
def display_live_data(parser: MQTTEnergyDataParser, interval: int = 30):
    """Display data secara live setiap interval detik"""
    while parser.is_running:
        try:
            devices = parser.get_device_list()
            recent_data = parser.get_all_recent_data(10)
            
            print("\n" + "="*80)
            print(f"LIVE MONITORING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Active Devices: {len(devices)}")
            print("="*80)
            
            for device in devices[:10]:  # Show top 10 devices
                print(f"Device {device['device_address']:>3}: "
                      f"{device['total_messages']:>5} msgs, "
                      f"Power: {device['last_avg_power']:>8.1f}W, "
                      f"Energy: {device['last_total_energy']:>8.2f}kWh")
            
            if recent_data:
                print("\nRecent Data:")
                for data in recent_data[:5]:
                    print(f"  {data['device_address']:>3}: {data['avg_power']:>8.1f}W "
                          f"@ {datetime.fromtimestamp(data['timestamp']).strftime('%H:%M:%S')}")
            
            time.sleep(interval)
            
        except Exception as e:
            logger.error(f"Error in live display: {e}")
            time.sleep(interval)

# Main function
def main():
    # Konfigurasi MQTT - PERBAIKAN: topic yang benar
    mqtt_config = {
        'host': '103.87.67.139',
        'port': 1883,
        'topic': 'energy/pzem/data',  # Topic yang benar sesuai log
        # 'username': 'your_mqtt_username',  # Uncomment jika perlu auth
        # 'password': 'your_mqtt_password'
    }
    
    # Konfigurasi database
    db_config = {
        'host': 'localhost',
        'database': 'energy_monitoring',
        'user': 'postgres',
        'password': 'Admin123',
        'port': 5432
    }
    
    # Inisialisasi parser
    parser = MQTTEnergyDataParser(mqtt_config, db_config)
    
    # Test mode - untuk debugging koneksi MQTT
    import sys
    test_mode = '--test' in sys.argv
    
    try:
        if test_mode:
            logger.info("[TEST] Running in TEST MODE - will only test MQTT connection")
            if parser.connect_database():
                parser.create_tables()
                parser.setup_mqtt_client()
                
                # Connect ke MQTT broker
                parser.mqtt_client.connect(
                    mqtt_config['host'],
                    mqtt_config.get('port', 1883),
                    60
                )
                
                parser.mqtt_client.loop_start()
                parser.test_connection()
                parser.mqtt_client.loop_stop()
                parser.mqtt_client.disconnect()
            
            parser.close_connection()
            return
        
        # Normal mode - production monitoring
        logger.info("🚀 Starting MQTT Energy Data Parser in PRODUCTION MODE...")
        
        # Start live display dalam thread terpisah
        display_thread = threading.Thread(
            target=display_live_data,
            args=(parser, 30),  # Update setiap 30 detik
            daemon=True
        )
        display_thread.start()
        
        # Start main monitoring
        parser.start_monitoring()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        parser.stop()
        logger.info("Program terminated")

# Fungsi untuk debugging MQTT sederhana
def simple_mqtt_test():
    """Test MQTT connection sederhana tanpa database"""
    import paho.mqtt.client as mqtt
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"[CONNECT] Connected to MQTT broker!")
            client.subscribe('energy/pzem/data')
            client.subscribe('#')  # Subscribe ke semua topic
        else:
            print(f"[ERROR] Failed to connect, return code {rc}")
    
    def on_message(client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            print(f"[TOPIC] {msg.topic}")
            print(f"[DATA] {payload[:500]}...")
            print("-" * 50)
        except Exception as e:
            print(f"[ERROR] {e}")
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print("[TEST] Testing MQTT connection to 103.87.67.139:1883...")
        client.connect('103.87.67.139', 1883, 60)
        client.loop_start()
        
        print("[WAIT] Listening for messages for 60 seconds...")
        time.sleep(60)
        
    except Exception as e:
        print(f"[ERROR] Connection error: {e}")
    finally:
        client.loop_stop()
        client.disconnect()
        print("[DONE] Disconnected")

if __name__ == "__main__":
    # Cek apakah running dengan flag --simple-test
    if '--simple-test' in sys.argv:
        simple_mqtt_test()
    else:
        main()
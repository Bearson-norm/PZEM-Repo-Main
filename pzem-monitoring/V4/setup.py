#!/usr/bin/env python3
"""
Script setup untuk sistem PZEM monitoring yang sudah diperbaiki
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging
import subprocess
import sys
import os
from datetime import datetime

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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemSetup:
    def __init__(self):
        self.connection = None
    
    def check_requirements(self):
        """Cek requirements sistem"""
        logger.info("🔍 Checking system requirements...")
        
        requirements = {
            'python': True,
            'pip': True,
            'psycopg2': False,
            'flask': False,
            'flask_socketio': False,
            'paho_mqtt': False
        }
        
        # Check Python packages
        try:
            import psycopg2
            requirements['psycopg2'] = True
        except ImportError:
            pass
        
        try:
            import flask
            requirements['flask'] = True
        except ImportError:
            pass
        
        try:
            import flask_socketio
            requirements['flask_socketio'] = True
        except ImportError:
            pass
        
        try:
            import paho.mqtt.client
            requirements['paho_mqtt'] = True
        except ImportError:
            pass
        
        logger.info("📋 Requirements status:")
        for req, status in requirements.items():
            status_icon = "✅" if status else "❌"
            logger.info(f"   {status_icon} {req}: {'OK' if status else 'Missing'}")
        
        missing = [req for req, status in requirements.items() if not status]
        
        if missing:
            logger.warning(f"⚠️  Missing requirements: {', '.join(missing)}")
            install_choice = input("Install missing requirements? (y/n): ").lower()
            if install_choice == 'y':
                return self.install_requirements(missing)
            else:
                logger.info("Please install missing requirements manually")
                return False
        
        logger.info("✅ All requirements satisfied")
        return True
    
    def install_requirements(self, missing):
        """Install missing Python packages"""
        logger.info("📦 Installing missing packages...")
        
        package_map = {
            'psycopg2': 'psycopg2-binary',
            'flask': 'Flask',
            'flask_socketio': 'Flask-SocketIO',
            'paho_mqtt': 'paho-mqtt'
        }
        
        try:
            for req in missing:
                if req in package_map:
                    package_name = package_map[req]
                    logger.info(f"Installing {package_name}...")
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package_name])
                    logger.info(f"✅ {package_name} installed successfully")
            
            logger.info("✅ All packages installed")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install packages: {e}")
            return False
    
    def test_database_connection(self):
        """Test koneksi database"""
        logger.info("🔌 Testing database connection...")
        
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            cursor = self.connection.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            logger.info("✅ Database connection successful")
            logger.info(f"📊 PostgreSQL version: {version.split(',')[0]}")
            
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            logger.error("💡 Please check:")
            logger.error("   1. PostgreSQL is running")
            logger.error("   2. Database 'pzem_monitoring' exists")
            logger.error("   3. User credentials are correct")
            return False
    
    def create_database_if_not_exists(self):
        """Buat database jika belum ada"""
        logger.info("🗄️  Checking database existence...")
        
        try:
            # Connect ke postgres database untuk create database
            temp_config = DB_CONFIG.copy()
            temp_config['database'] = 'postgres'
            
            temp_conn = psycopg2.connect(**temp_config)
            temp_conn.autocommit = True
            cursor = temp_conn.cursor()
            
            # Check if database exists
            cursor.execute("""
                SELECT EXISTS(
                    SELECT datname FROM pg_catalog.pg_database 
                    WHERE datname = %s
                );
            """, (DB_CONFIG['database'],))
            
            db_exists = cursor.fetchone()[0]
            
            if not db_exists:
                logger.info(f"🏗️  Creating database '{DB_CONFIG['database']}'...")
                cursor.execute(f"CREATE DATABASE {DB_CONFIG['database']};")
                logger.info("✅ Database created successfully")
            else:
                logger.info(f"✅ Database '{DB_CONFIG['database']}' already exists")
            
            cursor.close()
            temp_conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Error with database creation: {e}")
            return False
    
    def setup_new_database_structure(self):
        """Setup struktur database baru"""
        logger.info("🏗️  Setting up new database structure...")
        
        try:
            cursor = self.connection.cursor()
            
            # Create new tables
            create_tables_sql = """
            -- Drop existing tables
            DROP TABLE IF EXISTS pzem_data CASCADE;
            DROP TABLE IF EXISTS pzem_devices CASCADE;
            
            -- Tabel utama dengan struktur yang disederhanakan
            CREATE TABLE pzem_data (
                id SERIAL PRIMARY KEY,
                device_address VARCHAR(20) NOT NULL,
                timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Basic measurements
                voltage DECIMAL(8,2),
                current DECIMAL(8,3),
                power DECIMAL(10,2),
                energy DECIMAL(12,3),
                frequency DECIMAL(6,2) DEFAULT 50.0,
                power_factor DECIMAL(5,3) DEFAULT 1.0,
                
                -- Additional data
                wifi_rssi INTEGER,
                device_timestamp BIGINT,
                
                -- Sampling info
                sample_interval INTEGER DEFAULT 60,
                sample_count INTEGER DEFAULT 1,
                
                -- Status
                device_status VARCHAR(20) DEFAULT 'online',
                data_quality VARCHAR(20) DEFAULT 'good',
                
                -- Timestamp
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Tabel untuk device metadata
            CREATE TABLE pzem_devices (
                device_address VARCHAR(20) PRIMARY KEY,
                device_name VARCHAR(100),
                location VARCHAR(100),
                installation_date DATE DEFAULT CURRENT_DATE,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_records INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Indexes untuk performance
            CREATE INDEX idx_device_timestamp ON pzem_data(device_address, timestamp_utc DESC);
            CREATE INDEX idx_device_created ON pzem_data(device_address, created_at DESC);
            CREATE INDEX idx_timestamp ON pzem_data(timestamp_utc DESC);
            CREATE INDEX idx_created_at ON pzem_data(created_at DESC);
            
            -- Trigger untuk update device metadata
            CREATE OR REPLACE FUNCTION update_device_metadata()
            RETURNS TRIGGER AS $
            BEGIN
                INSERT INTO pzem_devices (device_address, last_seen, total_records)
                VALUES (NEW.device_address, NEW.created_at, 1)
                ON CONFLICT (device_address) 
                DO UPDATE SET 
                    last_seen = NEW.created_at,
                    total_records = pzem_devices.total_records + 1,
                    updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $ LANGUAGE plpgsql;
            
            CREATE TRIGGER trigger_update_device_metadata
                AFTER INSERT ON pzem_data
                FOR EACH ROW
                EXECUTE FUNCTION update_device_metadata();
            """
            
            cursor.execute(create_tables_sql)
            self.connection.commit()
            cursor.close()
            
            logger.info("✅ Database structure created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up database structure: {e}")
            self.connection.rollback()
            return False
    
    def insert_sample_data(self):
        """Insert sample data untuk testing"""
        logger.info("📊 Inserting sample data for testing...")
        
        try:
            cursor = self.connection.cursor()
            
            sample_data = [
                {
                    'device_address': '001',
                    'voltage': 220.5,
                    'current': 1.25,
                    'power': 275.6,
                    'energy': 12.45,
                    'frequency': 50.1,
                    'power_factor': 0.95,
                    'wifi_rssi': -45,
                    'device_timestamp': int(datetime.now().timestamp())
                },
                {
                    'device_address': '002', 
                    'voltage': 218.9,
                    'current': 2.15,
                    'power': 470.6,
                    'energy': 28.91,
                    'frequency': 49.9,
                    'power_factor': 0.92,
                    'wifi_rssi': -52,
                    'device_timestamp': int(datetime.now().timestamp())
                },
                {
                    'device_address': '003',
                    'voltage': 221.2,
                    'current': 0.85,
                    'power': 188.0,
                    'energy': 8.73,
                    'frequency': 50.0,
                    'power_factor': 0.98,
                    'wifi_rssi': -38,
                    'device_timestamp': int(datetime.now().timestamp())
                }
            ]
            
            insert_query = """
            INSERT INTO pzem_data (
                device_address, voltage, current, power, energy, frequency,
                power_factor, wifi_rssi, device_timestamp, device_status, data_quality
            ) VALUES (
                %(device_address)s, %(voltage)s, %(current)s, %(power)s, %(energy)s,
                %(frequency)s, %(power_factor)s, %(wifi_rssi)s, %(device_timestamp)s,
                'online', 'sample'
            )
            """
            
            for data in sample_data:
                cursor.execute(insert_query, data)
            
            self.connection.commit()
            cursor.close()
            
            logger.info(f"✅ Inserted {len(sample_data)} sample records")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inserting sample data: {e}")
            self.connection.rollback()
            return False
    
    def verify_setup(self):
        """Verifikasi setup sudah benar"""
        logger.info("🔍 Verifying setup...")
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # Check tables exist
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name IN ('pzem_data', 'pzem_devices')
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            if len(tables) != 2:
                logger.error("❌ Not all required tables exist")
                return False
            
            # Check data
            cursor.execute("SELECT COUNT(*) as count FROM pzem_data;")
            data_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM pzem_devices;")
            device_count = cursor.fetchone()['count']
            
            # Test latest data query
            cursor.execute("""
                SELECT DISTINCT ON (device_address) 
                    device_address, voltage, current, power, created_at
                FROM pzem_data 
                ORDER BY device_address, created_at DESC
                LIMIT 3;
            """)
            latest_data = cursor.fetchall()
            
            cursor.close()
            
            logger.info("📊 Setup verification results:")
            logger.info(f"   - Tables created: ✅ 2/2")
            logger.info(f"   - Data records: ✅ {data_count}")
            logger.info(f"   - Device metadata: ✅ {device_count}")
            logger.info(f"   - Latest data query: ✅ {len(latest_data)} devices")
            
            if latest_data:
                logger.info("📋 Sample data preview:")
                for row in latest_data:
                    logger.info(f"   - Device {row['device_address']}: {row['power']}W, {row['voltage']}V")
            
            logger.info("✅ Setup verification successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup verification failed: {e}")
            return False
    
    def create_startup_scripts(self):
        """Buat script untuk start services"""
        logger.info("📝 Creating startup scripts...")
        
        try:
            # MQTT Client startup script
            mqtt_script = """#!/bin/bash
echo "🚀 Starting PZEM MQTT Client (Improved Version)..."
echo "📡 Listening for topic: energy/pzem/data"
echo "🗄️  Database: pzem_monitoring"
echo ""

python3 mqtt_client_improved.py
"""
            
            # Dashboard startup script  
            dashboard_script = """#!/bin/bash
echo "🚀 Starting PZEM Dashboard (Improved Version)..."
echo "🌐 Dashboard will be available at: http://localhost:5000"
echo "🗄️  Database: pzem_monitoring"
echo ""

python3 app_improved.py
"""
            
            # Combined startup script
            combined_script = """#!/bin/bash
echo "🚀 Starting PZEM Monitoring System (Improved Version)"
echo "============================================="
echo ""

# Check if database is accessible
echo "🔍 Checking database connection..."
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(host='localhost', database='pzem_monitoring', user='postgres', password='Admin123')
    print('✅ Database connection OK')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "Please check your database connection and try again"
    exit 1
fi

echo ""
echo "Starting services..."
echo "🔗 MQTT Client: Terminal 1"
echo "🌐 Dashboard: Terminal 2"  
echo ""
echo "Press Ctrl+C to stop"

# Start MQTT client in background
python3 mqtt_client_improved.py &
MQTT_PID=$!

# Start dashboard 
python3 app_improved.py &
DASH_PID=$!

# Wait for interrupt
trap 'echo "Stopping services..."; kill $MQTT_PID $DASH_PID; exit 0' INT

wait
"""
            
            # Write scripts
            scripts = {
                'start_mqtt.sh': mqtt_script,
                'start_dashboard.sh': dashboard_script,
                'start_all.sh': combined_script
            }
            
            for filename, content in scripts.items():
                with open(filename, 'w') as f:
                    f.write(content)
                
                # Make executable on Unix systems
                try:
                    os.chmod(filename, 0o755)
                except:
                    pass  # Ignore on Windows
                
                logger.info(f"✅ Created: {filename}")
            
            logger.info("✅ Startup scripts created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating startup scripts: {e}")
            return False

def main():
    """Main setup function"""
    logger.info("🚀 PZEM Monitoring System Setup (Improved Version)")
    logger.info("=" * 60)
    
    setup = SystemSetup()
    
    # Step 1: Check requirements
    logger.info("\n📋 Step 1: Checking requirements...")
    if not setup.check_requirements():
        return
    
    # Step 2: Create database if needed
    logger.info("\n🗄️  Step 2: Setting up database...")
    if not setup.create_database_if_not_exists():
        return
    
    # Step 3: Test database connection
    logger.info("\n🔌 Step 3: Testing database connection...")
    if not setup.test_database_connection():
        return
    
    # Step 4: Setup database structure
    logger.info("\n🏗️  Step 4: Creating database structure...")
    if not setup.setup_new_database_structure():
        return
    
    # Step 5: Insert sample data
    logger.info("\n📊 Step 5: Adding sample data...")
    if not setup.insert_sample_data():
        logger.warning("⚠️  Sample data insertion failed, but continuing...")
    
    # Step 6: Verify setup
    logger.info("\n🔍 Step 6: Verifying setup...")
    if not setup.verify_setup():
        return
    
    # Step 7: Create startup scripts
    logger.info("\n📝 Step 7: Creating startup scripts...")
    if not setup.create_startup_scripts():
        logger.warning("⚠️  Script creation failed, but setup is complete")
    
    # Success message
    logger.info("\n🎉 Setup completed successfully!")
    logger.info("\n💡 Next steps:")
    logger.info("   1. Start MQTT client: python3 mqtt_client_improved.py")
    logger.info("      or run: ./start_mqtt.sh")
    logger.info("   2. Start dashboard: python3 app_improved.py") 
    logger.info("      or run: ./start_dashboard.sh")
    logger.info("   3. Or start both: ./start_all.sh")
    logger.info("   4. Open browser: http://localhost:5000")
    logger.info("\n📡 MQTT Configuration:")
    logger.info("   - Broker: 103.87.67.139:1883")
    logger.info("   - Topic: energy/pzem/data (specific topic only)")
    logger.info("   - QoS: 1")
    logger.info("\n🗄️  Database Structure:")
    logger.info("   - Main table: pzem_data (simplified structure)")
    logger.info("   - Metadata table: pzem_devices (device info)")
    logger.info("   - Auto-indexing and triggers enabled")

if __name__ == "__main__":
    main()
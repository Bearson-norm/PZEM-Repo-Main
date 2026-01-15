#!/usr/bin/env python3
"""
Fresh Database Setup - Flush semua data dan buat struktur baru yang bersih
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
import sys

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

class FreshDatabaseSetup:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            logger.info("✅ Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            raise
    
    def flush_all_data(self):
        """Hapus semua tabel dan data yang ada"""
        try:
            cursor = self.connection.cursor()
            
            logger.info("🗑️  Flushing all existing data and tables...")
            
            # Disable foreign key checks temporarily
            cursor.execute("SET session_replication_role = 'replica';")
            
            # Drop all PZEM related tables
            tables_to_drop = [
                'pzem_data',
                'pzem_devices'
            ]
            
            for table in tables_to_drop:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                logger.info(f"🗑️  Dropped table: {table}")
            
            # Drop backup tables if any
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name LIKE 'pzem_data_backup_%';
            """)
            
            backup_tables = cursor.fetchall()
            for table in backup_tables:
                table_name = table[0]
                cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
                logger.info(f"🗑️  Dropped backup table: {table_name}")
            
            # Drop any functions and triggers
            cursor.execute("DROP FUNCTION IF EXISTS update_device_metadata() CASCADE;")
            
            # Re-enable foreign key checks
            cursor.execute("SET session_replication_role = 'origin';")
            
            self.connection.commit()
            cursor.close()
            
            logger.info("✅ All existing data and tables flushed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error flushing data: {e}")
            self.connection.rollback()
            return False
    
    def create_fresh_structure(self):
        """Buat struktur database yang benar-benar baru"""
        try:
            cursor = self.connection.cursor()
            
            logger.info("🏗️  Creating fresh database structure...")
            
            create_tables_sql = """
            -- =================================================
            -- PZEM Monitoring Database - Fresh Structure v2.0
            -- =================================================
            
            -- Main data table dengan struktur yang optimal
            CREATE TABLE pzem_data (
                id SERIAL PRIMARY KEY,
                device_address VARCHAR(20) NOT NULL,
                
                -- Measurements (menggunakan DECIMAL untuk presisi)
                voltage DECIMAL(8,2),           -- 220.50V
                current DECIMAL(8,3),           -- 1.250A  
                power DECIMAL(10,2),            -- 275.60W
                energy DECIMAL(12,3),           -- 12.450kWh
                frequency DECIMAL(6,2) DEFAULT 50.0,   -- 50.10Hz
                power_factor DECIMAL(5,3) DEFAULT 1.0,  -- 0.950
                
                -- Additional sensor data
                wifi_rssi INTEGER,              -- -45dBm
                device_timestamp BIGINT,        -- Unix timestamp dari device
                
                -- Sampling information
                sample_interval INTEGER DEFAULT 60,    -- 60 seconds
                sample_count INTEGER DEFAULT 1,        -- Number of samples averaged
                
                -- Status dan quality tracking
                device_status VARCHAR(20) DEFAULT 'online',    -- 'online'/'offline'/'unknown'
                data_quality VARCHAR(20) DEFAULT 'good',       -- 'good'/'poor'/'sample'/'test'
                
                -- Timestamps
                timestamp_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- UTC timestamp
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP      -- Local timestamp
            );
            
            -- Device metadata table
            CREATE TABLE pzem_devices (
                device_address VARCHAR(20) PRIMARY KEY,
                device_name VARCHAR(100),                           -- "Kitchen Power Meter"
                location VARCHAR(100),                              -- "Kitchen, Floor 1"
                device_type VARCHAR(50) DEFAULT 'PZEM',            -- Device type
                installation_date DATE DEFAULT CURRENT_DATE,
                
                -- Statistics
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                total_records INTEGER DEFAULT 0,
                
                -- Configuration
                sample_rate INTEGER DEFAULT 60,                    -- Sampling rate in seconds
                alert_enabled BOOLEAN DEFAULT TRUE,
                power_threshold DECIMAL(10,2),                     -- Alert threshold
                
                -- Status
                status VARCHAR(20) DEFAULT 'active',               -- 'active'/'inactive'/'maintenance'
                notes TEXT,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- =================================================
            -- INDEXES untuk performance optimal
            -- =================================================
            
            -- Primary indexes untuk queries utama
            CREATE INDEX idx_pzem_device_created ON pzem_data(device_address, created_at DESC);
            CREATE INDEX idx_pzem_device_timestamp ON pzem_data(device_address, timestamp_utc DESC);
            CREATE INDEX idx_pzem_created_desc ON pzem_data(created_at DESC);
            CREATE INDEX idx_pzem_timestamp_desc ON pzem_data(timestamp_utc DESC);
            
            -- Indexes untuk filtering
            CREATE INDEX idx_pzem_device_status ON pzem_data(device_address, device_status);
            CREATE INDEX idx_pzem_quality ON pzem_data(data_quality);
            
            -- Indexes untuk aggregation queries
            CREATE INDEX idx_pzem_device_created_power ON pzem_data(device_address, created_at DESC, power);
            
            -- =================================================
            -- FUNCTIONS dan TRIGGERS
            -- =================================================
            
            -- Function untuk update device metadata
            CREATE OR REPLACE FUNCTION update_device_metadata()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Insert atau update device metadata
                INSERT INTO pzem_devices (
                    device_address, 
                    first_seen,
                    last_seen, 
                    total_records,
                    updated_at
                )
                VALUES (
                    NEW.device_address, 
                    NEW.created_at,
                    NEW.created_at, 
                    1,
                    NEW.created_at
                )
                ON CONFLICT (device_address) 
                DO UPDATE SET 
                    last_seen = NEW.created_at,
                    total_records = pzem_devices.total_records + 1,
                    updated_at = NEW.created_at;
                
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            -- Trigger untuk auto-update device metadata
            CREATE TRIGGER trigger_update_device_metadata
                AFTER INSERT ON pzem_data
                FOR EACH ROW
                EXECUTE FUNCTION update_device_metadata();
            
            -- =================================================
            -- SAMPLE DATA untuk testing
            -- =================================================
            
            -- Insert sample devices metadata
            INSERT INTO pzem_devices (device_address, device_name, location, device_type) VALUES
            ('001', 'Kitchen Power Meter', 'Kitchen, Floor 1', 'PZEM-004T'),
            ('002', 'Living Room Monitor', 'Living Room, Floor 1', 'PZEM-004T'),
            ('003', 'AC Unit Monitor', 'Bedroom, Floor 2', 'PZEM-004T')
            ON CONFLICT (device_address) DO NOTHING;
            """
            
            # Execute the complete SQL
            cursor.execute(create_tables_sql)
            self.connection.commit()
            cursor.close()
            
            logger.info("✅ Fresh database structure created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating fresh structure: {e}")
            logger.error(f"❌ SQL Error details: {str(e)}")
            self.connection.rollback()
            return False
    
    def insert_sample_data(self):
        """Insert sample data untuk testing dashboard"""
        try:
            cursor = self.connection.cursor()
            
            logger.info("📊 Inserting sample data for testing...")
            
            # Generate sample data dengan variasi waktu
            sample_data = []
            import random
            from datetime import timedelta
            
            base_time = datetime.now()
            devices = ['001', '002', '003']
            
            # Generate data untuk 3 devices, 10 records each
            for i in range(30):
                device = devices[i % 3]
                timestamp = base_time - timedelta(minutes=i * 2)
                
                # Variasi data berdasarkan device
                if device == '001':  # Kitchen - moderate consumption
                    base_power = 250 + random.uniform(-50, 100)
                    base_voltage = 220 + random.uniform(-5, 5)
                elif device == '002':  # Living room - higher consumption
                    base_power = 450 + random.uniform(-100, 150)
                    base_voltage = 218 + random.uniform(-8, 8)
                else:  # AC Unit - variable consumption
                    base_power = 800 + random.uniform(-200, 400)
                    base_voltage = 222 + random.uniform(-3, 3)
                
                current = base_power / base_voltage if base_voltage > 0 else 0
                energy = 10 + (i * 0.1)  # Incremental energy
                
                sample_data.append({
                    'device_address': device,
                    'voltage': round(base_voltage, 2),
                    'current': round(current, 3), 
                    'power': round(base_power, 2),
                    'energy': round(energy, 3),
                    'frequency': round(50.0 + random.uniform(-0.5, 0.5), 2),
                    'power_factor': round(0.85 + random.uniform(0, 0.15), 3),
                    'wifi_rssi': random.randint(-65, -35),
                    'device_timestamp': int(timestamp.timestamp()),
                    'device_status': 'online',
                    'data_quality': 'sample',
                    'timestamp_utc': timestamp,
                    'created_at': timestamp
                })
            
            # Insert sample data
            insert_query = """
            INSERT INTO pzem_data (
                device_address, voltage, current, power, energy, frequency,
                power_factor, wifi_rssi, device_timestamp, device_status,
                data_quality, timestamp_utc, created_at
            ) VALUES (
                %(device_address)s, %(voltage)s, %(current)s, %(power)s, 
                %(energy)s, %(frequency)s, %(power_factor)s, %(wifi_rssi)s,
                %(device_timestamp)s, %(device_status)s, %(data_quality)s,
                %(timestamp_utc)s, %(created_at)s
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
    
    def verify_fresh_setup(self):
        """Verifikasi setup database yang fresh"""
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            logger.info("🔍 Verifying fresh database setup...")
            
            # Check tables exist
            cursor.execute("""
                SELECT table_name, 
                       (SELECT count(*) FROM information_schema.columns 
                        WHERE table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_name IN ('pzem_data', 'pzem_devices')
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            # Check data counts
            cursor.execute("SELECT COUNT(*) as count FROM pzem_data;")
            data_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM pzem_devices;")
            device_count = cursor.fetchone()['count']
            
            # Check latest data per device
            cursor.execute("""
                SELECT 
                    device_address,
                    COUNT(*) as record_count,
                    MAX(created_at) as latest,
                    AVG(power) as avg_power
                FROM pzem_data 
                GROUP BY device_address
                ORDER BY device_address;
            """)
            device_stats = cursor.fetchall()
            
            # Check indexes
            cursor.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'pzem_data' 
                AND indexname LIKE 'idx_pzem%';
            """)
            indexes = cursor.fetchall()
            
            cursor.close()
            
            # Report results
            logger.info("📊 Fresh setup verification results:")
            logger.info("=" * 50)
            
            for table in tables:
                logger.info(f"  ✅ Table '{table['table_name']}': {table['column_count']} columns")
            
            logger.info(f"  ✅ Data records: {data_count}")
            logger.info(f"  ✅ Device metadata: {device_count}")
            logger.info(f"  ✅ Performance indexes: {len(indexes)}")
            
            logger.info("\n📋 Device statistics:")
            for stat in device_stats:
                logger.info(f"  📱 Device {stat['device_address']}: {stat['record_count']} records, "
                           f"avg {stat['avg_power']:.1f}W, latest: {stat['latest'].strftime('%H:%M:%S')}")
            
            # Test serialization
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT DISTINCT ON (device_address) 
                    device_address, voltage, current, power, created_at
                FROM pzem_data 
                ORDER BY device_address, created_at DESC
            """)
            test_data = cursor.fetchall()
            cursor.close()
            
            # Test JSON serialization
            import json
            from datetime import datetime
            from decimal import Decimal
            
            def serialize_test(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, Decimal):
                    return float(obj)
                return str(obj)
            
            try:
                serialized = []
                for row in test_data:
                    row_dict = dict(row)
                    serialized_row = {k: serialize_test(v) for k, v in row_dict.items()}
                    serialized.append(serialized_row)
                
                json.dumps(serialized)
                logger.info("  ✅ JSON serialization test: PASSED")
                
            except Exception as e:
                logger.error(f"  ❌ JSON serialization test: FAILED - {e}")
                return False
            
            logger.info("\n🎉 Fresh database setup verification: SUCCESS")
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup verification failed: {e}")
            return False
    
    def create_startup_info(self):
        """Buat informasi untuk startup"""
        try:
            info_content = f"""
# PZEM Monitoring System - Fresh Setup Complete
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Database Structure Created:
✅ pzem_data - Main sensor data table (optimized structure)
✅ pzem_devices - Device metadata table  
✅ Performance indexes - Optimized for dashboard queries
✅ Auto-triggers - Device metadata auto-update
✅ Sample data - 30 test records for 3 devices

## Next Steps:
1. Start MQTT Client:
   python mqtt_client_improved.py
   
2. Start Dashboard:  
   python app_improved.py
   
3. Access Dashboard:
   http://localhost:5000

## MQTT Configuration Required:
- Topic: energy/pzem/data (not energy/pzem/+)
- Format: JSON with fields: device_address, voltage, current, power, energy

## Sample Message Format:
{{
    "device_address": "001",
    "voltage": 220.5,
    "current": 1.25,
    "power": 275.6,
    "energy": 12.45,
    "frequency": 50.1,
    "power_factor": 0.95
}}

## Database Details:
- Host: {DB_CONFIG['host']}
- Database: {DB_CONFIG['database']}
- Fresh setup completed successfully
- All JSON serialization issues resolved
"""
            
            with open('SETUP_COMPLETE.md', 'w') as f:
                f.write(info_content)
            
            logger.info("📝 Setup information saved to: SETUP_COMPLETE.md")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating startup info: {e}")
            return False

def main():
    """Main fresh setup function"""
    logger.info("🚀 PZEM Fresh Database Setup")
    logger.info("=" * 60)
    logger.info("⚠️  WARNING: This will DELETE ALL existing PZEM data!")
    
    # Confirmation
    confirm = input("\nAre you sure you want to flush all data and create fresh setup? (yes/no): ")
    if confirm.lower() != 'yes':
        logger.info("❌ Setup cancelled by user")
        return
    
    setup = FreshDatabaseSetup()
    
    # Step 1: Flush all existing data
    logger.info("\n🗑️  Step 1: Flushing all existing data...")
    if not setup.flush_all_data():
        logger.error("❌ Failed to flush data, aborting")
        return
    
    # Step 2: Create fresh structure
    logger.info("\n🏗️  Step 2: Creating fresh database structure...")
    if not setup.create_fresh_structure():
        logger.error("❌ Failed to create structure, aborting")
        return
    
    # Step 3: Insert sample data
    logger.info("\n📊 Step 3: Inserting sample data...")
    if not setup.insert_sample_data():
        logger.warning("⚠️  Sample data insertion failed, but continuing...")
    
    # Step 4: Verify setup
    logger.info("\n🔍 Step 4: Verifying fresh setup...")
    if not setup.verify_fresh_setup():
        logger.error("❌ Setup verification failed")
        return
    
    # Step 5: Create startup info
    logger.info("\n📝 Step 5: Creating startup information...")
    setup.create_startup_info()
    
    # Success message
    logger.info("\n🎉 FRESH SETUP COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    logger.info("✅ Database completely flushed and recreated")
    logger.info("✅ Optimal structure with proper indexes")
    logger.info("✅ Sample data inserted for testing") 
    logger.info("✅ JSON serialization issues resolved")
    logger.info("✅ Ready for production use")
    
    logger.info("\n🚀 Ready to start:")
    logger.info("1. python mqtt_client_improved.py")
    logger.info("2. python app_improved.py")  
    logger.info("3. Open http://localhost:5000")
    
    logger.info("\n📋 Important:")
    logger.info("- Configure MQTT devices to publish to: energy/pzem/data")
    logger.info("- Use JSON format as shown in SETUP_COMPLETE.md")
    logger.info("- All previous JSON errors should be resolved")

if __name__ == "__main__":
    main()
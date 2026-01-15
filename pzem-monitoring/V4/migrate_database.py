#!/usr/bin/env python3
"""
Script migrasi database dari struktur lama ke struktur baru yang lebih sederhana
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
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
    level=logging.DEBUG,  # Changed to DEBUG for detailed logging
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
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
    
    def backup_existing_data(self):
        """Backup data lama sebelum migrasi"""
        try:
            cursor = self.connection.cursor()
            
            # Cek apakah tabel lama ada
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pzem_data'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                logger.info("⚠️  No existing pzem_data table found, skipping backup")
                cursor.close()
                return True
            
            # Hitung jumlah records
            cursor.execute("SELECT COUNT(*) FROM pzem_data;")
            record_count = cursor.fetchone()[0]
            
            if record_count == 0:
                logger.info("⚠️  No data in existing table, skipping backup")
                cursor.close()
                return True
            
            logger.info(f"📊 Found {record_count} records in existing table")
            
            # Create backup table
            backup_table_name = f"pzem_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            cursor.execute(f"""
                CREATE TABLE {backup_table_name} AS 
                SELECT * FROM pzem_data;
            """)
            
            self.connection.commit()
            cursor.close()
            
            logger.info(f"✅ Backup created: {backup_table_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating backup: {e}")
            return False
    
    def create_new_structure(self):
        """Buat struktur database yang baru"""
        try:
            cursor = self.connection.cursor()
            
            # Drop existing table
            logger.info("🗑️  Dropping existing pzem_data table...")
            cursor.execute("DROP TABLE IF EXISTS pzem_data CASCADE;")
            
            # Create new structure
            logger.info("🏗️  Creating new table structure...")
            
            create_tables_sql = """
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
            RETURNS TRIGGER AS $$
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
            $$ LANGUAGE plpgsql;
            
            CREATE TRIGGER trigger_update_device_metadata
                AFTER INSERT ON pzem_data
                FOR EACH ROW
                EXECUTE FUNCTION update_device_metadata();
            """
            
            cursor.execute(create_tables_sql)
            self.connection.commit()
            cursor.close()
            
            logger.info("✅ New database structure created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating new structure: {e}")
            self.connection.rollback()
            return False
    
    def migrate_existing_data(self):
        """Migrasi data dari backup ke struktur baru"""
        try:
            cursor = self.connection.cursor()
            
            # Cari backup table terbaru
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name LIKE 'pzem_data_backup_%' 
                ORDER BY table_name DESC 
                LIMIT 1;
            """)
            
            backup_table = cursor.fetchone()
            
            if not backup_table:
                logger.info("⚠️  No backup table found, skipping data migration")
                cursor.close()
                return True
            
            backup_table_name = backup_table[0]
            logger.info(f"📥 Migrating data from {backup_table_name}")
            
            # Cek struktur backup table
            cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{backup_table_name}'
                ORDER BY ordinal_position;
            """)
            
            backup_columns = cursor.fetchall()
            logger.info(f"📋 Backup table has {len(backup_columns)} columns")
            
            # Map kolom lama ke kolom baru
            column_mapping = {
                'device_address': 'device_address',
                'avg_voltage': 'voltage',
                'current_voltage': 'voltage',
                'avg_current': 'current',
                'current_current': 'current',
                'avg_power': 'power',
                'current_active_power': 'power',
                'total_energy': 'energy',
                'current_active_energy': 'energy',
                'current_frequency': 'frequency',
                'current_power_factor': 'power_factor',
                'wifi_rssi': 'wifi_rssi',
                'timestamp_data': 'device_timestamp',
                'interval_minutes': 'sample_interval',
                'sample_count': 'sample_count',
                'created_at': 'created_at'
            }
            
            # Build migration query
            select_fields = []
            for old_col, new_col in column_mapping.items():
                # Cek apakah kolom ada di backup table
                col_exists = any(col[0] == old_col for col in backup_columns)
                if col_exists:
                    select_fields.append(f"{old_col} as {new_col}")
                else:
                    # Default values untuk kolom yang tidak ada
                    if new_col == 'frequency':
                        select_fields.append("50.0 as frequency")
                    elif new_col == 'power_factor':
                        select_fields.append("1.0 as power_factor")
                    elif new_col == 'device_status':
                        select_fields.append("'online' as device_status")
                    elif new_col == 'data_quality':
                        select_fields.append("'migrated' as data_quality")
            
            if not select_fields:
                logger.error("❌ No compatible columns found for migration")
                cursor.close()
                return False
            
            # Insert migrated data
            migration_query = f"""
            INSERT INTO pzem_data ({', '.join(column_mapping.values())})
            SELECT {', '.join(select_fields)}
            FROM {backup_table_name}
            ORDER BY created_at;
            """
            
            logger.info("🔄 Executing data migration...")
            cursor.execute(migration_query)
            
            # Get migration results
            cursor.execute("SELECT COUNT(*) FROM pzem_data;")
            migrated_count = cursor.fetchone()[0]
            
            self.connection.commit()
            cursor.close()
            
            logger.info(f"✅ Successfully migrated {migrated_count} records")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error migrating data: {e}")
            self.connection.rollback()
            return False
    
    def verify_migration(self):
        """Verifikasi hasil migrasi"""
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # Hitung total records
            cursor.execute("SELECT COUNT(*) as total FROM pzem_data;")
            total_records = cursor.fetchone()['total']
            
            # Hitung unique devices
            cursor.execute("SELECT COUNT(DISTINCT device_address) as devices FROM pzem_data;")
            total_devices = cursor.fetchone()['devices']
            
            # Sample data terbaru
            cursor.execute("""
                SELECT device_address, voltage, current, power, created_at
                FROM pzem_data 
                ORDER BY created_at DESC 
                LIMIT 5;
            """)
            sample_data = cursor.fetchall()
            
            # Check device metadata
            cursor.execute("SELECT COUNT(*) as devices FROM pzem_devices;")
            metadata_devices = cursor.fetchone()['devices']
            
            cursor.close()
            
            logger.info("📊 Migration Verification Results:")
            logger.info(f"   - Total records: {total_records}")
            logger.info(f"   - Unique devices: {total_devices}")
            logger.info(f"   - Device metadata records: {metadata_devices}")
            
            if sample_data:
                logger.info("📋 Sample migrated data:")
                for row in sample_data:
                    logger.info(f"   - Device {row['device_address']}: {row['power']}W, {row['voltage']}V at {row['created_at']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error verifying migration: {e}")
            return False
    
    def cleanup_backup_tables(self, keep_latest=True):
        """Bersihkan tabel backup lama (opsional)"""
        try:
            cursor = self.connection.cursor()
            
            # Cari semua backup tables
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name LIKE 'pzem_data_backup_%' 
                ORDER BY table_name DESC;
            """)
            
            backup_tables = cursor.fetchall()
            
            if not backup_tables:
                logger.info("ℹ️  No backup tables to cleanup")
                cursor.close()
                return True
            
            tables_to_drop = backup_tables[1:] if keep_latest else backup_tables
            
            if not tables_to_drop:
                logger.info(f"ℹ️  Keeping latest backup table: {backup_tables[0][0]}")
                cursor.close()
                return True
            
            for table in tables_to_drop:
                table_name = table[0]
                logger.info(f"🗑️  Dropping backup table: {table_name}")
                cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
            
            self.connection.commit()
            cursor.close()
            
            logger.info(f"✅ Cleaned up {len(tables_to_drop)} backup tables")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up backup tables: {e}")
            return False

def main():
    """Main migration function"""
    logger.info("🔄 Starting PZEM Database Migration")
    logger.info("=" * 50)
    
    try:
        migrator = DatabaseMigrator()
        
        # Step 1: Backup existing data
        logger.info("\n📦 Step 1: Backing up existing data...")
        if not migrator.backup_existing_data():
            logger.error("❌ Backup failed, aborting migration")
            return
        
        # Step 2: Create new structure
        logger.info("\n🏗️  Step 2: Creating new database structure...")
        if not migrator.create_new_structure():
            logger.error("❌ Structure creation failed, aborting migration")
            return
        
        # Step 3: Migrate data
        logger.info("\n🔄 Step 3: Migrating existing data...")
        if not migrator.migrate_existing_data():
            logger.error("❌ Data migration failed")
            return
        
        # Step 4: Verify migration
        logger.info("\n✅ Step 4: Verifying migration...")
        if not migrator.verify_migration():
            logger.error("❌ Migration verification failed")
            return
        
        # Optional: Cleanup
        logger.info("\n🧹 Step 5: Cleanup (optional)")
        cleanup_choice = input("Do you want to keep backup tables? (y/n): ").lower()
        if cleanup_choice == 'n':
            migrator.cleanup_backup_tables(keep_latest=True)
        
        logger.info("\n🎉 Migration completed successfully!")
        logger.info("💡 You can now:")
        logger.info("   1. Run the new MQTT client: python mqtt_client_improved.py")
        logger.info("   2. Run the new dashboard: python app_improved.py")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        logger.error("💡 Please check your database connection and try again")

if __name__ == "__main__":
    main()
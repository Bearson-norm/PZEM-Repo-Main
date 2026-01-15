#!/usr/bin/env python3
"""
Debug script untuk melihat struktur tabel lama dan merencanakan migrasi
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging

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

def analyze_backup_table():
    """Analisis struktur tabel backup"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Cari backup table
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name LIKE 'pzem_data_backup_%' 
            ORDER BY table_name DESC 
            LIMIT 1;
        """)
        
        backup_table = cursor.fetchone()
        if not backup_table:
            logger.error("❌ No backup table found")
            return
            
        backup_table_name = backup_table['table_name']
        logger.info(f"🔍 Analyzing table: {backup_table_name}")
        
        # Ambil struktur kolom
        cursor.execute(f"""
            SELECT 
                column_name, 
                data_type, 
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = '{backup_table_name}'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        
        logger.info(f"📋 Found {len(columns)} columns:")
        logger.info("=" * 60)
        
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
            logger.info(f"  {col['column_name']:<25} {col['data_type']:<15} {nullable}{default}")
        
        # Ambil sample data
        logger.info("\n📊 Sample data from backup:")
        logger.info("=" * 60)
        
        cursor.execute(f"""
            SELECT * FROM {backup_table_name} 
            ORDER BY created_at DESC 
            LIMIT 2;
        """)
        
        samples = cursor.fetchall()
        
        for i, sample in enumerate(samples):
            logger.info(f"\n--- Sample {i+1} ---")
            for key, value in sample.items():
                if value is not None:
                    logger.info(f"  {key}: {value} ({type(value).__name__})")
        
        # Analisis kolom yang penting untuk migrasi
        logger.info("\n🎯 Migration Analysis:")
        logger.info("=" * 60)
        
        important_columns = {
            'device_address': 'Device identifier',
            'avg_voltage': 'Average voltage',
            'current_voltage': 'Current voltage',
            'avg_current': 'Average current',
            'current_current': 'Current current',
            'avg_power': 'Average power',
            'current_active_power': 'Current power',
            'total_energy': 'Total energy',
            'current_active_energy': 'Current energy',
            'current_frequency': 'Frequency',
            'current_power_factor': 'Power factor',
            'wifi_rssi': 'WiFi signal strength',
            'timestamp_data': 'Device timestamp',
            'created_at': 'Record timestamp'
        }
        
        available_columns = [col['column_name'] for col in columns]
        
        for col, description in important_columns.items():
            status = "✅ Available" if col in available_columns else "❌ Missing"
            logger.info(f"  {col:<25} {status:<15} - {description}")
        
        # Rekomendasi mapping
        logger.info("\n💡 Recommended column mapping:")
        logger.info("=" * 60)
        
        mappings = [
            ('device_address', 'device_address'),
            ('avg_voltage OR current_voltage', 'voltage'),
            ('avg_current OR current_current', 'current'),
            ('avg_power OR current_active_power', 'power'),
            ('total_energy OR current_active_energy', 'energy'),
            ('current_frequency', 'frequency'),
            ('current_power_factor', 'power_factor'),
            ('wifi_rssi', 'wifi_rssi'),
            ('timestamp_data', 'device_timestamp'),
            ('created_at', 'created_at')
        ]
        
        for old_col, new_col in mappings:
            logger.info(f"  {old_col:<30} -> {new_col}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error analyzing backup table: {e}")

def create_safe_migration_query():
    """Buat query migrasi yang aman"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Cari backup table
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name LIKE 'pzem_data_backup_%' 
            ORDER BY table_name DESC 
            LIMIT 1;
        """)
        
        backup_table = cursor.fetchone()
        if not backup_table:
            logger.error("❌ No backup table found")
            return
            
        backup_table_name = backup_table[0]
        
        # Cek kolom yang ada
        cursor.execute(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '{backup_table_name}';
        """)
        
        available_columns = [row[0] for row in cursor.fetchall()]
        
        # Build safe migration query
        logger.info("\n🔧 Safe migration query:")
        logger.info("=" * 60)
        
        select_parts = []
        
        # Device address (required)
        if 'device_address' in available_columns:
            select_parts.append("device_address")
        else:
            logger.error("❌ device_address not found - migration not possible")
            return
        
        # Voltage (prefer avg_voltage)
        if 'avg_voltage' in available_columns:
            select_parts.append("avg_voltage as voltage")
        elif 'current_voltage' in available_columns:
            select_parts.append("current_voltage as voltage")
        else:
            select_parts.append("NULL as voltage")
        
        # Current (prefer avg_current)
        if 'avg_current' in available_columns:
            select_parts.append("avg_current as current")
        elif 'current_current' in available_columns:
            select_parts.append("current_current as current")
        else:
            select_parts.append("NULL as current")
        
        # Power (prefer avg_power)
        if 'avg_power' in available_columns:
            select_parts.append("avg_power as power")
        elif 'current_active_power' in available_columns:
            select_parts.append("current_active_power as power")
        else:
            select_parts.append("NULL as power")
        
        # Energy
        if 'total_energy' in available_columns:
            select_parts.append("total_energy as energy")
        elif 'current_active_energy' in available_columns:
            select_parts.append("current_active_energy as energy")
        else:
            select_parts.append("NULL as energy")
        
        # Frequency
        if 'current_frequency' in available_columns:
            select_parts.append("current_frequency as frequency")
        else:
            select_parts.append("50.0 as frequency")
        
        # Power factor
        if 'current_power_factor' in available_columns:
            select_parts.append("current_power_factor as power_factor")
        else:
            select_parts.append("1.0 as power_factor")
        
        # WiFi RSSI
        if 'wifi_rssi' in available_columns:
            select_parts.append("wifi_rssi")
        else:
            select_parts.append("NULL as wifi_rssi")
        
        # Device timestamp
        if 'timestamp_data' in available_columns:
            select_parts.append("timestamp_data as device_timestamp")
        else:
            select_parts.append("NULL as device_timestamp")
        
        # Additional fields
        select_parts.extend([
            "60 as sample_interval",
            "1 as sample_count", 
            "'online' as device_status",
            "'migrated' as data_quality"
        ])
        
        # Created at
        if 'created_at' in available_columns:
            select_parts.append("created_at")
        else:
            select_parts.append("CURRENT_TIMESTAMP as created_at")
        
        # Build final query
        query = f"""
INSERT INTO pzem_data (
    device_address, voltage, current, power, energy, frequency,
    power_factor, wifi_rssi, device_timestamp, sample_interval,
    sample_count, device_status, data_quality, created_at
)
SELECT 
    {',\\n    '.join(select_parts)}
FROM {backup_table_name}
WHERE device_address IS NOT NULL
ORDER BY created_at;
"""
        
        logger.info(query)
        
        # Save to file
        with open('safe_migration.sql', 'w') as f:
            f.write(query)
        
        logger.info("\n✅ Safe migration query saved to: safe_migration.sql")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error creating safe migration query: {e}")

def main():
    """Main function"""
    logger.info("🔍 PZEM Migration Debug Tool")
    logger.info("=" * 50)
    
    # Analyze backup table
    analyze_backup_table()
    
    # Create safe migration query
    create_safe_migration_query()
    
    logger.info("\n💡 Next steps:")
    logger.info("1. Review the analysis above")
    logger.info("2. Check safe_migration.sql file")
    logger.info("3. Run the corrected migrate_database.py")

if __name__ == "__main__":
    main()
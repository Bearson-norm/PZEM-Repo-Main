#!/usr/bin/env python3
"""
Database Debug Tool - Check database connection and data
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json

# Database config - pastikan sama dengan config di file lain
DB_CONFIG = {
    'host': 'localhost',
    'database': 'pzem_monitoring',
    'user': 'postgres',
    'password': 'Admin123'
}

def test_database_connection():
    """Test database connection dan struktur tabel"""
    try:
        print("Testing database connection...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("✓ Database connection successful")
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        print(f"Available tables: {[t['table_name'] for t in tables]}")
        
        # Check pzem_data table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'pzem_data'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        print("\npzem_data table structure:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable']=='YES' else 'NOT NULL'})")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def check_recent_data():
    """Check recent data in database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Count total records
        cursor.execute("SELECT COUNT(*) as total FROM pzem_data")
        total = cursor.fetchone()['total']
        print(f"\nTotal records in pzem_data: {total}")
        
        # Check data from last 24 hours
        cursor.execute("""
            SELECT COUNT(*) as count, MIN(created_at) as oldest, MAX(created_at) as newest
            FROM pzem_data 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        recent = cursor.fetchone()
        print(f"Records in last 24 hours: {recent['count']}")
        print(f"Date range: {recent['oldest']} to {recent['newest']}")
        
        # Check unique devices
        cursor.execute("""
            SELECT device_address, COUNT(*) as count, MAX(created_at) as last_seen
            FROM pzem_data 
            GROUP BY device_address 
            ORDER BY device_address
        """)
        devices = cursor.fetchall()
        print(f"\nDevices found: {len(devices)}")
        for device in devices:
            print(f"  Device {device['device_address']}: {device['count']} records, last seen: {device['last_seen']}")
        
        # Show sample recent data
        cursor.execute("""
            SELECT device_address, voltage, current, power, energy, created_at
            FROM pzem_data 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        samples = cursor.fetchall()
        print(f"\nRecent 10 records:")
        for sample in samples:
            print(f"  Device {sample['device_address']}: {sample['power']}W, {sample['voltage']}V at {sample['created_at']}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error checking data: {e}")
        return False

def test_report_query():
    """Test the exact query used by report generator"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test query for daily report (same as in report_generator.py)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        print(f"\nTesting report query from {start_date} to {end_date}")
        
        query = """
        SELECT 
            device_address,
            COUNT(*) as total_records,
            AVG(voltage) as avg_voltage,
            AVG(current) as avg_current,
            AVG(power) as avg_power,
            AVG(frequency) as avg_frequency,
            AVG(power_factor) as avg_power_factor,
            MAX(energy) - MIN(energy) as energy_consumed,
            MIN(created_at) as period_start,
            MAX(created_at) as period_end,
            MIN(voltage) as min_voltage,
            MAX(voltage) as max_voltage,
            MIN(current) as min_current,
            MAX(current) as max_current,
            MIN(power) as min_power,
            MAX(power) as max_power
        FROM pzem_data 
        WHERE created_at >= %s AND created_at <= %s
        GROUP BY device_address
        ORDER BY device_address
        """
        
        cursor.execute(query, (start_date, end_date))
        results = cursor.fetchall()
        
        print(f"Query returned {len(results)} devices:")
        for result in results:
            print(f"  Device {result['device_address']}:")
            print(f"    Records: {result['total_records']}")
            print(f"    Avg Power: {result['avg_power']:.2f}W")
            print(f"    Avg Voltage: {result['avg_voltage']:.2f}V")
            print(f"    Energy: {result['energy_consumed']:.3f}kWh")
            print(f"    Period: {result['period_start']} to {result['period_end']}")
            print()
        
        cursor.close()
        conn.close()
        
        return len(results) > 0
        
    except Exception as e:
        print(f"✗ Error testing report query: {e}")
        return False

def fix_missing_columns():
    """Fix any missing columns that might cause issues"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("\nChecking and adding missing columns...")
        
        # Add frequency column if missing (with default value)
        try:
            cursor.execute("""
                ALTER TABLE pzem_data 
                ADD COLUMN IF NOT EXISTS frequency DECIMAL(6,2) DEFAULT 50.0
            """)
            print("✓ Added frequency column")
        except Exception as e:
            print(f"  Frequency column: {e}")
        
        # Add power_factor column if missing
        try:
            cursor.execute("""
                ALTER TABLE pzem_data 
                ADD COLUMN IF NOT EXISTS power_factor DECIMAL(5,3) DEFAULT 1.0
            """)
            print("✓ Added power_factor column")
        except Exception as e:
            print(f"  Power factor column: {e}")
        
        # Update NULL values
        cursor.execute("""
            UPDATE pzem_data 
            SET frequency = 50.0 
            WHERE frequency IS NULL
        """)
        
        cursor.execute("""
            UPDATE pzem_data 
            SET power_factor = 1.0 
            WHERE power_factor IS NULL
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✓ Database structure updated")
        return True
        
    except Exception as e:
        print(f"✗ Error fixing columns: {e}")
        return False

def test_report_generation():
    """Test basic report generation"""
    try:
        print("\nTesting report generation...")
        
        # Import and test report generator
        from report_generator import DatabaseManager, ReportGenerator
        
        db_manager = DatabaseManager()
        report_gen = ReportGenerator(db_manager)
        
        # Test data retrieval
        data = db_manager.get_report_data('daily')
        
        if data and data['phase_data']:
            print(f"✓ Report data retrieved: {len(data['phase_data'])} phases")
            for phase in data['phase_data']:
                print(f"  Phase {phase['device_address']}: {phase['avg_power']:.1f}W")
            
            # Try to generate a test report
            report_file = report_gen.generate_report('daily')
            if report_file:
                print(f"✓ Test report generated: {report_file}")
                return True
            else:
                print("✗ Report generation failed")
                return False
        else:
            print("✗ No report data available")
            return False
            
    except Exception as e:
        print(f"✗ Error testing report generation: {e}")
        return False

def main():
    """Main debug function"""
    print("PZEM Database Debug Tool")
    print("=" * 50)
    
    # Test 1: Database connection
    if not test_database_connection():
        return
    
    # Test 2: Check recent data
    if not check_recent_data():
        return
    
    # Test 3: Fix missing columns
    fix_missing_columns()
    
    # Test 4: Test report query
    if not test_report_query():
        print("Report query failed - no data in time range")
        return
    
    # Test 5: Test report generation
    test_report_generation()
    
    print("\nDebug completed!")

if __name__ == "__main__":
    main()
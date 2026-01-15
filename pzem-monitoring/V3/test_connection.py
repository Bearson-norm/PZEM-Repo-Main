#!/usr/bin/env python3
"""
Script untuk testing koneksi database dan memeriksa data
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
from decimal import Decimal

# Database config
DB_CONFIG = {
    'host': 'localhost',
    'database': 'pzem_monitoring',
    'user': 'postgres',
    'password': 'Admin123'
}

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super(CustomJSONEncoder, self).default(obj)

def test_database_connection():
    """Test koneksi database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Database connection successful!")
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test query sederhana
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"PostgreSQL version: {version['version']}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_table_exists():
    """Cek apakah tabel pzem_data exists"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'pzem_data'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ Table 'pzem_data' exists")
            
            # Hitung jumlah records
            cursor.execute("SELECT COUNT(*) FROM pzem_data;")
            count = cursor.fetchone()[0]
            print(f"📊 Total records: {count}")
            
            # Ambil devices yang ada
            cursor.execute("SELECT DISTINCT device_address FROM pzem_data ORDER BY device_address;")
            devices = cursor.fetchall()
            print(f"📱 Available devices: {[d[0] for d in devices]}")
            
        else:
            print("❌ Table 'pzem_data' does not exist")
            print("💡 Please run the MQTT client first to create the table")
        
        cursor.close()
        conn.close()
        return table_exists
        
    except Exception as e:
        print(f"❌ Error checking table: {e}")
        return False

def test_data_serialization():
    """Test serialisasi data seperti yang dilakukan di dashboard"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Ambil sample data
        cursor.execute("SELECT * FROM pzem_data ORDER BY created_at DESC LIMIT 1;")
        sample_data = cursor.fetchone()
        
        if sample_data:
            print("✅ Sample data found")
            
            # Convert to dict
            data_dict = dict(sample_data)
            
            # Test JSON serialization
            json_str = json.dumps(data_dict, cls=CustomJSONEncoder, indent=2)
            print("✅ JSON serialization successful")
            print(f"📄 Sample JSON:\n{json_str[:500]}...")
            
        else:
            print("⚠️  No data found in table")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing serialization: {e}")
        return False

def test_latest_data_query():
    """Test query untuk mendapatkan latest data semua device"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT DISTINCT ON (device_address) 
            device_address,
            avg_voltage,
            avg_current, 
            avg_power,
            total_energy,
            created_at
        FROM pzem_data 
        ORDER BY device_address, created_at DESC
        """
        
        cursor.execute(query)
        latest_data = cursor.fetchall()
        
        if latest_data:
            print(f"✅ Found latest data for {len(latest_data)} devices")
            
            # Serialize and test
            result = {}
            for row in latest_data:
                device_data = dict(row)
                # Serialize datetime objects
                for key, value in device_data.items():
                    if isinstance(value, datetime):
                        device_data[key] = value.isoformat()
                    elif isinstance(value, Decimal):
                        device_data[key] = float(value)
                
                result[row['device_address']] = device_data
            
            json_str = json.dumps(result, indent=2)
            print("✅ Latest data serialization successful")
            print(f"📄 Latest data preview:\n{json_str[:300]}...")
            
        else:
            print("⚠️  No latest data found")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing latest data query: {e}")
        return False

def main():
    """Main testing function"""
    print("🔍 PZEM Database Connection & Data Test")
    print("=" * 50)
    
    # Test 1: Database connection
    print("\n1. Testing database connection...")
    if not test_database_connection():
        return
    
    # Test 2: Check table exists
    print("\n2. Checking table existence...")
    if not check_table_exists():
        return
    
    # Test 3: Test data serialization
    print("\n3. Testing data serialization...")
    test_data_serialization()
    
    # Test 4: Test latest data query
    print("\n4. Testing latest data query...")
    test_latest_data_query()
    
    print("\n✅ All tests completed!")
    print("💡 If all tests pass, your dashboard should work without JSON errors")

if __name__ == "__main__":
    main()
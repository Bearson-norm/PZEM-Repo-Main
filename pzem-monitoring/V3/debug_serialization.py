#!/usr/bin/env python3
"""
Script debug khusus untuk mengecek serialization data dari database
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

def serialize_data(data):
    """Convert datetime objects and Decimals to JSON serializable formats"""
    if isinstance(data, list):
        return [serialize_data(item) for item in data]
    elif isinstance(data, dict):
        return {key: serialize_data(value) for key, value in data.items()}
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return data

def debug_raw_data():
    """Debug raw data dari database"""
    print("🔍 Debugging raw data from database...")
    
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
        LIMIT 2
        """
        
        cursor.execute(query)
        raw_data = cursor.fetchall()
        
        print(f"📊 Found {len(raw_data)} records")
        
        for i, row in enumerate(raw_data):
            print(f"\n--- Record {i+1} ---")
            row_dict = dict(row)
            
            for key, value in row_dict.items():
                print(f"  {key}: {value} ({type(value).__name__})")
            
            # Test JSON serialization tanpa custom encoder
            print("\n🧪 Testing raw JSON serialization...")
            try:
                json_str = json.dumps(row_dict)
                print("✅ Raw JSON OK")
            except Exception as e:
                print(f"❌ Raw JSON Error: {e}")
            
            # Test dengan serialize_data function
            print("\n🧪 Testing with serialize_data...")
            try:
                serialized = serialize_data(row_dict)
                json_str = json.dumps(serialized)
                print("✅ Serialized JSON OK")
                print(f"📄 Serialized: {json_str[:100]}...")
            except Exception as e:
                print(f"❌ Serialized JSON Error: {e}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

def debug_get_all_latest_simulation():
    """Simulate get_all_latest_data method"""
    print("\n🔍 Simulating get_all_latest_data method...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT DISTINCT ON (device_address) 
            device_address,
            timestamp_data,
            wifi_rssi,
            avg_voltage,
            avg_current, 
            avg_power,
            total_energy,
            current_voltage,
            current_current,
            current_active_power,
            current_power_factor,
            created_at
        FROM pzem_data 
        ORDER BY device_address, created_at DESC
        """
        
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        
        print(f"📊 Query returned {len(data)} devices")
        
        # Convert to dictionary with device_address as key and serialize
        result = {}
        for row in data:
            device_data = dict(row)
            device_address = row['device_address']
            
            print(f"\n--- Processing Device {device_address} ---")
            
            # Debug setiap field
            for key, value in device_data.items():
                if value is not None:
                    print(f"  {key}: {type(value).__name__} = {value}")
            
            # Serialize data
            serialized_data = serialize_data(device_data)
            result[device_address] = serialized_data
            
            # Test JSON serialization untuk device ini
            try:
                json.dumps(serialized_data)
                print(f"✅ Device {device_address} JSON OK")
            except Exception as e:
                print(f"❌ Device {device_address} JSON Error: {e}")
        
        # Test final result
        print(f"\n🧪 Testing final result with {len(result)} devices...")
        try:
            json_str = json.dumps(result)
            print("✅ Final result JSON OK")
            print(f"📄 Size: {len(json_str)} characters")
        except Exception as e:
            print(f"❌ Final result JSON Error: {e}")
            return None
        
        conn.close()
        return result
        
    except Exception as e:
        print(f"❌ Simulation error: {e}")
        return None

def debug_specific_types():
    """Debug specific data types yang bermasalah"""
    print("\n🔍 Debugging specific problematic types...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Cek data types di database
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'pzem_data'
            ORDER BY column_name;
        """)
        
        columns = cursor.fetchall()
        print("📋 Table column types:")
        for col in columns:
            print(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
        
        # Ambil sample data dengan semua kolom
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM pzem_data ORDER BY created_at DESC LIMIT 1;")
        sample = cursor.fetchone()
        
        if sample:
            print(f"\n📊 Sample data types:")
            sample_dict = dict(sample)
            
            problematic_fields = []
            for key, value in sample_dict.items():
                type_name = type(value).__name__
                print(f"  {key}: {type_name} = {value}")
                
                # Test individual JSON serialization
                try:
                    json.dumps(value, default=str)
                except Exception as e:
                    problematic_fields.append((key, type_name, str(e)))
            
            if problematic_fields:
                print(f"\n❌ Problematic fields found:")
                for field, field_type, error in problematic_fields:
                    print(f"  {field} ({field_type}): {error}")
            else:
                print(f"\n✅ All individual fields can be JSON serialized")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Type debug error: {e}")

def main():
    """Main debug function"""
    print("🔧 PZEM Dashboard Serialization Debug")
    print("=" * 60)
    
    # Debug 1: Raw data
    debug_raw_data()
    
    # Debug 2: Simulate get_all_latest_data
    result = debug_get_all_latest_simulation()
    
    # Debug 3: Specific types
    debug_specific_types()
    
    if result:
        print(f"\n✅ Debugging completed successfully!")
        print(f"💡 Try importing this data in your Flask app")
    else:
        print(f"\n❌ Debugging found issues that need to be fixed")

if __name__ == "__main__":
    main()
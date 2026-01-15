#!/usr/bin/env python3
"""
Debug script untuk mengecek data dashboard
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
    elif data is None:
        return None
    elif isinstance(data, (int, float, str, bool)):
        return data
    else:
        return str(data)

def check_devices_api():
    """Debug /api/devices endpoint"""
    print("=== DEBUG: /api/devices endpoint ===")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query yang sama dengan API
        query = """
        SELECT 
            d.device_address,
            COALESCE(dm.device_name, 'Device ' || d.device_address) as device_name,
            COALESCE(dm.location, 'Unknown') as location,
            COUNT(d.id) as data_count,
            MAX(d.created_at) as last_seen,
            AVG(d.power) as avg_power,
            AVG(d.voltage) as avg_voltage,
            AVG(d.current) as avg_current,
            MAX(d.energy) as total_energy,
            COALESCE(dm.status, 'active') as device_status
        FROM pzem_data d
        LEFT JOIN pzem_devices dm ON d.device_address = dm.device_address
        GROUP BY d.device_address, dm.device_name, dm.location, dm.status
        ORDER BY d.device_address
        """
        
        cursor.execute(query)
        devices = cursor.fetchall()
        
        print(f"Found {len(devices)} devices:")
        for device in devices:
            device_dict = dict(device)
            serialized = serialize_data(device_dict)
            print(f"\nDevice: {device['device_address']}")
            print(f"  - Name: {device['device_name']}")
            print(f"  - Data count: {device['data_count']}")
            print(f"  - Avg power: {device['avg_power']}")
            print(f"  - Last seen: {device['last_seen']}")
            print(f"  - JSON: {json.dumps(serialized, indent=2)}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR in devices API: {e}")

def check_all_latest_api():
    """Debug /api/all-latest endpoint"""
    print("\n=== DEBUG: /api/all-latest endpoint ===")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query yang sama dengan API
        query = """
        SELECT DISTINCT ON (device_address) 
            device_address,
            voltage,
            current,
            power,
            energy,
            frequency,
            power_factor,
            wifi_rssi,
            device_timestamp,
            device_status,
            data_quality,
            timestamp_utc,
            created_at
        FROM pzem_data 
        ORDER BY device_address, created_at DESC
        """
        
        cursor.execute(query)
        data = cursor.fetchall()
        
        print(f"Found latest data for {len(data)} devices:")
        
        # Convert to dictionary format seperti API
        result = {}
        for row in data:
            device_data = dict(row)
            device_address = row['device_address']
            serialized_data = serialize_data(device_data)
            result[device_address] = serialized_data
            
            print(f"\nDevice {device_address}:")
            print(f"  - Power: {row['power']}")
            print(f"  - Voltage: {row['voltage']}")
            print(f"  - Current: {row['current']}")
            print(f"  - Created: {row['created_at']}")
        
        # Test JSON serialization
        json_result = json.dumps(result, indent=2)
        print(f"\nJSON Output length: {len(json_result)} characters")
        print(f"Sample JSON:\n{json_result[:500]}...")
        
        cursor.close()
        conn.close()
        
        return result
        
    except Exception as e:
        print(f"ERROR in all-latest API: {e}")
        return {}

def check_raw_data():
    """Debug raw data di database"""
    print("\n=== DEBUG: Raw database data ===")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check pzem_data table
        cursor.execute("SELECT COUNT(*) as total FROM pzem_data;")
        total = cursor.fetchone()['total']
        print(f"Total records in pzem_data: {total}")
        
        # Check distinct devices
        cursor.execute("SELECT DISTINCT device_address FROM pzem_data ORDER BY device_address;")
        devices = cursor.fetchall()
        print(f"Distinct devices: {[d['device_address'] for d in devices]}")
        
        # Check latest records
        cursor.execute("""
            SELECT device_address, power, voltage, current, created_at 
            FROM pzem_data 
            ORDER BY created_at DESC 
            LIMIT 5;
        """)
        latest = cursor.fetchall()
        
        print("\nLatest 5 records:")
        for record in latest:
            print(f"  Device {record['device_address']}: {record['power']}W at {record['created_at']}")
        
        # Check pzem_devices table
        cursor.execute("SELECT * FROM pzem_devices;")
        metadata = cursor.fetchall()
        
        print(f"\nDevice metadata records: {len(metadata)}")
        for device in metadata:
            print(f"  {device['device_address']}: {device.get('device_name', 'No name')}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR checking raw data: {e}")

def simulate_frontend_processing(api_data):
    """Simulate bagaimana frontend memproses data"""
    print("\n=== DEBUG: Frontend processing simulation ===")
    
    if not api_data:
        print("No API data to process")
        return
    
    print("Processing device list...")
    device_count = len(api_data)
    print(f"Device count: {device_count}")
    
    for device_address, device_data in api_data.items():
        print(f"\nProcessing device {device_address}:")
        
        # Check data structure
        power = device_data.get('power', 0)
        voltage = device_data.get('voltage', 0) 
        current = device_data.get('current', 0)
        energy = device_data.get('energy', 0)
        created_at = device_data.get('created_at')
        
        print(f"  - power: {power} ({type(power)})")
        print(f"  - voltage: {voltage} ({type(voltage)})")  
        print(f"  - current: {current} ({type(current)})")
        print(f"  - energy: {energy} ({type(energy)})")
        print(f"  - created_at: {created_at}")
        
        # Check for None/null values
        if power is None:
            print("  - WARNING: power is None/null")
        if voltage is None:
            print("  - WARNING: voltage is None/null")
        if current is None:
            print("  - WARNING: current is None/null")

def check_javascript_format():
    """Check format yang diharapkan JavaScript"""
    print("\n=== DEBUG: Expected JavaScript format ===")
    
    expected_format = {
        "001": {
            "device_address": "001",
            "power": 275.6,  # Should be number, not null
            "voltage": 220.5,  # Should be number, not null  
            "current": 1.25,   # Should be number, not null
            "energy": 12.45,   # Should be number, not null
            "created_at": "2025-09-03T15:27:45"
        }
    }
    
    print("Expected format for /api/all-latest:")
    print(json.dumps(expected_format, indent=2))

def main():
    print("PZEM Dashboard Data Debug Tool")
    print("=" * 50)
    
    # Debug steps
    check_raw_data()
    check_devices_api()
    latest_data = check_all_latest_api()
    simulate_frontend_processing(latest_data)
    check_javascript_format()
    
    print("\n" + "=" * 50)
    print("Debug completed. Check output above for issues.")

if __name__ == "__main__":
    main()
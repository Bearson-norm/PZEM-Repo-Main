#!/usr/bin/env python3
"""
Script untuk debug dan test sistem PZEM Monitoring
"""

import psycopg2
import paho.mqtt.client as mqtt
import json
import time
import sys

# Database config
DB_CONFIG = {
    'host': 'localhost',
    'database': 'pzem_monitoring',
    'user': 'postgres',
    'password': 'Admin123'
}

# MQTT config
MQTT_BROKER = "103.87.67.139"
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/pzem/+"

def test_database_connection():
    """Test koneksi ke database"""
    print("=" * 50)
    print("1. Testing Database Connection...")
    print("=" * 50)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Test basic connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Database connection successful!")
        print(f"   PostgreSQL version: {version}")
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'pzem_data'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            print("✅ Table 'pzem_data' exists")
            
            # Count records
            cursor.execute("SELECT COUNT(*) FROM pzem_data;")
            record_count = cursor.fetchone()[0]
            print(f"📊 Records in database: {record_count}")
            
            if record_count > 0:
                # Show latest record
                cursor.execute("""
                    SELECT device_address, created_at, avg_power, avg_voltage 
                    FROM pzem_data 
                    ORDER BY created_at DESC 
                    LIMIT 1;
                """)
                latest = cursor.fetchone()
                print(f"🔍 Latest record: Device {latest[0]}, {latest[1]}, {latest[2]}W, {latest[3]}V")
            else:
                print("⚠️  No data found in database")
                
        else:
            print("❌ Table 'pzem_data' does not exist!")
            print("   Run the database setup first")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_mqtt_connection():
    """Test koneksi ke MQTT broker"""
    print("\n" + "=" * 50)
    print("2. Testing MQTT Connection...")
    print("=" * 50)
    
    connected = False
    messages_received = 0
    
    def on_connect(client, userdata, flags, rc):
        nonlocal connected
        if rc == 0:
            print("✅ MQTT connection successful!")
            print(f"   Broker: {MQTT_BROKER}:{MQTT_PORT}")
            print(f"   Subscribing to: {MQTT_TOPIC}")
            client.subscribe(MQTT_TOPIC)
            connected = True
        else:
            print(f"❌ MQTT connection failed with code {rc}")
            
    def on_message(client, userdata, msg):
        nonlocal messages_received
        messages_received += 1
        print(f"📨 Message {messages_received} received from topic: {msg.topic}")
        try:
            data = json.loads(msg.payload.decode('utf-8'))
            device_address = data.get('device_address', 'Unknown')
            power = data.get('avg_power', 0)
            voltage = data.get('avg_voltage', 0)
            print(f"   Device: {device_address}, Power: {power}W, Voltage: {voltage}V")
        except:
            print(f"   Raw payload: {msg.payload[:100]}...")
            
    def on_disconnect(client, userdata, rc):
        print("⚠️  MQTT disconnected")
    
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        
        print(f"Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Listen for 30 seconds
        print("Listening for messages (30 seconds)...")
        start_time = time.time()
        
        while time.time() - start_time < 30:
            client.loop(timeout=1.0)
            if not connected:
                time.sleep(1)
                
        client.disconnect()
        
        if connected:
            if messages_received > 0:
                print(f"✅ Received {messages_received} messages")
            else:
                print("⚠️  No messages received (devices might be offline)")
        
        return connected
        
    except Exception as e:
        print(f"❌ MQTT connection error: {e}")
        return False

def create_sample_data():
    """Buat sample data untuk testing"""
    print("\n" + "=" * 50)
    print("3. Creating Sample Data...")
    print("=" * 50)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Insert sample data
        sample_data = [
            ('001', time.time() * 1000, -65, 220.5, 1.2, 264.6, 45.8),
            ('002', time.time() * 1000, -70, 221.0, 0.8, 176.8, 32.1),
            ('003', time.time() * 1000, -68, 219.8, 1.5, 329.7, 52.4),
        ]
        
        for device_addr, timestamp, rssi, voltage, current, power, energy in sample_data:
            cursor.execute("""
                INSERT INTO pzem_data (
                    device_address, timestamp_data, wifi_rssi, avg_voltage, 
                    avg_current, avg_power, total_energy
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (device_addr, timestamp, rssi, voltage, current, power, energy))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Sample data created for {len(sample_data)} devices")
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False

def check_processes():
    """Check if required processes are running"""
    print("\n" + "=" * 50)
    print("4. Checking Running Processes...")
    print("=" * 50)
    
    import subprocess
    
    try:
        # Check if any Python MQTT clients are running
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        processes = result.stdout
        
        mqtt_processes = [line for line in processes.split('\n') if 'mqtt_client.py' in line]
        flask_processes = [line for line in processes.split('\n') if 'app.py' in line]
        
        if mqtt_processes:
            print("✅ MQTT client process found:")
            for proc in mqtt_processes:
                print(f"   {proc.strip()}")
        else:
            print("❌ No MQTT client process running!")
            print("   Start with: python mqtt_client.py")
        
        if flask_processes:
            print("✅ Flask app process found:")
            for proc in flask_processes:
                print(f"   {proc.strip()}")
        else:
            print("⚠️  No Flask app process running")
            print("   Start with: python app.py")
            
    except Exception as e:
        print(f"Error checking processes: {e}")

def main():
    print("PZEM Monitoring System Debug Tool")
    print("=" * 50)
    
    # Test 1: Database
    db_ok = test_database_connection()
    
    # Test 2: MQTT (optional)
    mqtt_ok = False
    response = input("\nTest MQTT connection? (y/n): ").lower()
    if response == 'y':
        mqtt_ok = test_mqtt_connection()
    
    # Test 3: Create sample data if no data exists
    if db_ok:
        response = input("\nCreate sample data for testing? (y/n): ").lower()
        if response == 'y':
            create_sample_data()
    
    # Test 4: Check processes
    check_processes()
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    if not db_ok:
        print("❌ Fix database connection first")
        print("   - Check PostgreSQL is running")
        print("   - Check database credentials in config")
        print("   - Run database setup script")
    
    print("\nTo start the complete system:")
    print("1. Terminal 1: python mqtt_client.py")
    print("2. Terminal 2: python app.py")
    print("3. Open browser: http://localhost:5000")
    
    if not mqtt_ok and response == 'y':
        print("\n⚠️  MQTT Issues:")
        print("   - Check if MQTT broker is accessible")
        print("   - Check if devices are sending data")
        print("   - Verify topic names match")

if __name__ == "__main__":
    main()
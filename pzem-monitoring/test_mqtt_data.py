#!/usr/bin/env python3
"""
Script untuk mengirim test data MQTT ke sistem monitoring PZEM
"""

import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

# Konfigurasi MQTT
MQTT_BROKER = "103.87.67.139"
MQTT_PORT = 1883
MQTT_TOPIC_BASE = "sensor/pzem/"

def generate_test_data(device_id):
    """Generate test data sesuai format PZEM"""
    current_time = int(time.time())
    
    # Generate data yang realistis
    voltage = round(220 + random.uniform(-10, 10), 2)
    current = round(random.uniform(10, 40), 3)
    power = round(voltage * current * random.uniform(0.8, 0.95), 1)  # Dengan power factor
    energy = round(random.uniform(10, 100), 3)
    
    test_data = {
        "device_address": str(device_id),
        "timestamp": current_time,
        "wifi_rssi": random.randint(-80, -30),
        "interval_minutes": 5,
        "sample_count": random.randint(250, 350),
        "period_start": current_time - 300,  # 5 menit yang lalu
        "period_end": current_time,
        "avg_voltage": voltage,
        "avg_current": current,
        "avg_power": power,
        "total_energy": energy,
        "min_voltage": voltage - random.uniform(1, 5),
        "max_voltage": voltage + random.uniform(1, 5),
        "min_current": current - random.uniform(1, 3),
        "max_current": current + random.uniform(1, 3),
        "min_power": power - random.uniform(50, 200),
        "max_power": power + random.uniform(50, 200),
        "current_data": {
            "enabled": True,
            "address": device_id,
            "time": current_time,
            "frequency": 50.0,
            "voltage": voltage + random.uniform(-2, 2),
            "current": current + random.uniform(-1, 1),
            "active_power": power + random.uniform(-100, 100),
            "reactive_power": power * random.uniform(0.3, 0.7),
            "apparent_power": power * random.uniform(1.1, 1.3),
            "power_factor": round(random.uniform(0.85, 0.95), 2),
            "active_energy": energy + random.uniform(-5, 5),
            "resistance": round(voltage / current, 3),
            "dimmed_voltage": voltage * 0.5,
            "nominal_power": power * 1.2,
            "thdi": round(random.uniform(1, 5), 3)
        }
    }
    
    return test_data

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker successfully")
    else:
        print(f"❌ Failed to connect to MQTT broker, return code {rc}")

def on_publish(client, userdata, mid):
    print(f"📤 Data published successfully (Message ID: {mid})")

def on_disconnect(client, userdata, rc):
    print("📡 Disconnected from MQTT broker")

def main():
    print("🔧 PZEM MQTT Test Data Sender")
    print("="*40)
    
    # Setup MQTT client
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        client.on_connect = on_connect
        client.on_publish = on_publish
        client.on_disconnect = on_disconnect
        
        print(f"🔗 Connecting to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        time.sleep(2)  # Wait for connection
        
        # Menu
        while True:
            print("\n📋 Menu:")
            print("1. Send single test data")
            print("2. Send continuous data (every 30s)")
            print("3. Send data for multiple devices")
            print("4. Exit")
            
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == '1':
                device_id = input("Enter device ID (1-10): ").strip()
                try:
                    device_id = int(device_id)
                    if 1 <= device_id <= 10:
                        data = generate_test_data(device_id)
                        topic = f"{MQTT_TOPIC_BASE}{device_id}"
                        
                        print(f"\n📨 Sending data to topic: {topic}")
                        print(f"📊 Data preview: Device {device_id}, Power: {data['avg_power']}W")
                        
                        result = client.publish(topic, json.dumps(data), qos=1)
                        
                        if result.rc == mqtt.MQTT_ERR_SUCCESS:
                            print("✅ Data sent successfully!")
                        else:
                            print(f"❌ Failed to send data: {result.rc}")
                    else:
                        print("❌ Device ID must be between 1-10")
                except ValueError:
                    print("❌ Invalid device ID")
            
            elif choice == '2':
                device_id = input("Enter device ID (1-10): ").strip()
                try:
                    device_id = int(device_id)
                    if 1 <= device_id <= 10:
                        print(f"\n🔄 Starting continuous data for device {device_id}")
                        print("Press Ctrl+C to stop")
                        
                        try:
                            while True:
                                data = generate_test_data(device_id)
                                topic = f"{MQTT_TOPIC_BASE}{device_id}"
                                
                                current_time = datetime.now().strftime("%H:%M:%S")
                                print(f"[{current_time}] 📊 Sending data - Power: {data['avg_power']}W, Voltage: {data['avg_voltage']}V")
                                
                                client.publish(topic, json.dumps(data), qos=1)
                                time.sleep(30)  # Send every 30 seconds
                                
                        except KeyboardInterrupt:
                            print("\n⏹️ Stopped continuous sending")
                    else:
                        print("❌ Device ID must be between 1-10")
                except ValueError:
                    print("❌ Invalid device ID")
            
            elif choice == '3':
                num_devices = input("Enter number of devices (1-5): ").strip()
                try:
                    num_devices = int(num_devices)
                    if 1 <= num_devices <= 5:
                        print(f"\n📤 Sending data for {num_devices} devices")
                        
                        for device_id in range(1, num_devices + 1):
                            data = generate_test_data(device_id)
                            topic = f"{MQTT_TOPIC_BASE}{device_id}"
                            
                            print(f"📨 Device {device_id}: Power {data['avg_power']}W")
                            client.publish(topic, json.dumps(data), qos=1)
                            time.sleep(1)  # Small delay between devices
                        
                        print("✅ All data sent!")
                    else:
                        print("❌ Number of devices must be between 1-5")
                except ValueError:
                    print("❌ Invalid number")
            
            elif choice == '4':
                print("👋 Exiting...")
                break
            
            else:
                print("❌ Invalid option")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except:
            pass

if __name__ == "__main__":
    main()
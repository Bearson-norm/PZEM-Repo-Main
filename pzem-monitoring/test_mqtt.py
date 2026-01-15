#!/usr/bin/env python3
"""
Test MQTT Client untuk debug komunikasi dengan broker
"""

import json
import paho.mqtt.client as mqtt
import time
import sys

# Konfigurasi MQTT
MQTT_BROKER = "103.87.67.139"
MQTT_PORT = 1883
MQTT_TOPICS = [
    "sensor/pzem/+",      # Topic dari kode asli
    "sensor/pzem/1",      # Topic spesifik untuk device 1
    "#",                  # Subscribe semua topic (untuk debug)
]

class MQTTTester:
    def __init__(self):
        self.messages_received = 0
        self.client = None
        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        """Callback ketika koneksi berhasil/gagal"""
        if rc == 0:
            print(f"✅ Connected to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
            self.connected = True
            
            # Subscribe ke berbagai topic untuk test
            for topic in MQTT_TOPICS:
                client.subscribe(topic)
                print(f"📡 Subscribed to: {topic}")
                
        else:
            print(f"❌ Connection failed with code {rc}")
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier", 
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            print(f"   Error: {error_messages.get(rc, 'Unknown error')}")
            self.connected = False

    def on_message(self, client, userdata, msg):
        """Callback ketika menerima pesan"""
        self.messages_received += 1
        
        print(f"\n📨 Message {self.messages_received}")
        print(f"   Topic: {msg.topic}")
        print(f"   QoS: {msg.qos}")
        print(f"   Retain: {msg.retain}")
        print(f"   Payload size: {len(msg.payload)} bytes")
        
        try:
            # Decode payload
            payload_str = msg.payload.decode('utf-8')
            print(f"   Raw payload: {payload_str[:200]}...")
            
            # Parse JSON
            data = json.loads(payload_str)
            print(f"   ✅ Valid JSON received")
            print(f"   Device: {data.get('device_address', 'Unknown')}")
            print(f"   Power: {data.get('avg_power', 0)}W")
            print(f"   Voltage: {data.get('avg_voltage', 0)}V")
            print(f"   Current: {data.get('avg_current', 0)}A")
            print(f"   Energy: {data.get('total_energy', 0)}kWh")
            
            # Check current_data
            current_data = data.get('current_data', {})
            if current_data:
                print(f"   Current Power: {current_data.get('active_power', 0)}W")
                print(f"   Power Factor: {current_data.get('power_factor', 0)}")
            
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON decode error: {e}")
            print(f"   Raw data: {msg.payload}")
        except UnicodeDecodeError as e:
            print(f"   ❌ Unicode decode error: {e}")
            print(f"   Raw bytes: {msg.payload}")
        except Exception as e:
            print(f"   ❌ Other error: {e}")

    def on_disconnect(self, client, userdata, rc):
        """Callback ketika terputus"""
        if rc != 0:
            print("⚠️  Unexpected disconnection!")
        else:
            print("📡 Disconnected from broker")
        self.connected = False

    def on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback ketika subscribe berhasil"""
        print(f"✅ Subscription confirmed (QoS: {granted_qos})")

    def test_connection(self, duration=60):
        """Test koneksi MQTT untuk durasi tertentu"""
        print("=" * 50)
        print("MQTT Connection Test")
        print("=" * 50)
        print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"Test duration: {duration} seconds")
        print("=" * 50)

        try:
            # Setup client
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message  
            self.client.on_disconnect = self.on_disconnect
            self.client.on_subscribe = self.on_subscribe

            # Set username/password jika diperlukan
            # self.client.username_pw_set("username", "password")

            print("Connecting to broker...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)

            # Start loop and wait
            self.client.loop_start()
            
            start_time = time.time()
            last_message_count = 0
            
            while time.time() - start_time < duration:
                elapsed = int(time.time() - start_time)
                remaining = duration - elapsed
                
                if self.messages_received != last_message_count:
                    last_message_count = self.messages_received
                
                print(f"\r⏱️  Time: {elapsed}s/{duration}s | Messages: {self.messages_received} | Remaining: {remaining}s", end="")
                time.sleep(1)

            print("\n")
            self.client.loop_stop()
            self.client.disconnect()

            # Summary
            print("=" * 50)
            print("TEST RESULTS")
            print("=" * 50)
            print(f"Connection successful: {self.connected}")
            print(f"Total messages received: {self.messages_received}")
            
            if self.messages_received == 0:
                print("\n❌ No messages received. Possible issues:")
                print("1. Device tidak mengirim data ke broker")
                print("2. Topic tidak match")
                print("3. Firewall blocking connection")
                print("4. Broker requires authentication")
                
                print("\n🔍 Debugging tips:")
                print("1. Check Node-RED flow - apakah publish ke broker yang sama?")
                print("2. Check topic name di Node-RED vs Python")
                print("3. Test dengan MQTT client lain (mosquitto_sub)")
            else:
                print(f"✅ Receiving data successfully!")
                
        except Exception as e:
            print(f"\n❌ Connection error: {e}")

    def test_specific_topic(self, topic, duration=30):
        """Test topic spesifik"""
        print(f"\nTesting specific topic: {topic}")
        
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            self.client.on_connect = lambda c, u, f, rc: c.subscribe(topic) if rc == 0 else None
            self.client.on_message = self.on_message
            
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            
            time.sleep(duration)
            
            self.client.loop_stop()
            self.client.disconnect()
            
        except Exception as e:
            print(f"Error testing topic {topic}: {e}")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("MQTT Test Client")
            print("Usage: python test_mqtt.py [duration]")
            print("  duration: Test duration in seconds (default: 60)")
            return
    
    # Get duration from command line or use default
    duration = 60
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print("Invalid duration, using default 60 seconds")
    
    tester = MQTTTester()
    tester.test_connection(duration)
    
    # Test beberapa topic spesifik juga
    print(f"\n" + "=" * 50)
    print("TESTING SPECIFIC TOPICS")
    print("=" * 50)
    
    specific_topics = [
        "sensor/pzem/1",
        "pzem/1", 
        "sensor/1",
        "device/1/pzem"
    ]
    
    for topic in specific_topics:
        print(f"\nTesting topic: {topic}")
        tester_specific = MQTTTester()
        tester_specific.test_specific_topic(topic, 10)

if __name__ == "__main__":
    main()
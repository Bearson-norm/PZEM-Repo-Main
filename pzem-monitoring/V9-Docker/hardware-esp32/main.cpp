/*
 * PZEM004Tv3 dengan pembacaan asinkron dan MQTT
 * 
 * Library yang diperlukan:
 * - MycilaPZEM004Tv3
 * - ArduinoJson
 * - WiFi
 * - PubSubClient
 * - AsyncTCP (untuk ESP32)
 */

#include <Arduino.h>
#include <ArduinoJson.h>
#include <MycilaPZEM004Tv3.h>
#include <WiFi.h>
#include <PubSubClient.h>

// Konfigurasi WiFi
const char* ssid = "FOOM-G2";
const char* password = "@FOOM2024";

// Konfigurasi MQTT
const char* mqtt_server = "103.87.67.139";
const int mqtt_port = 1883;
const char* mqtt_client_id = "ESP32_PZEM_003";
const char* mqtt_topic = "energy/pzem/data";
const char* mqtt_username = "";  // Kosongkan jika tidak ada username
const char* mqtt_password = "";  // Kosongkan jika tidak ada password

// Objek global
Mycila::PZEM pzem;
WiFiClient espClient;
PubSubClient mqtt_client(espClient);

// Variabel untuk timing asinkron
unsigned long lastPZEMRead = 0;
unsigned long lastMQTTSend = 0;
unsigned long lastMQTTReconnect = 0;
const unsigned long PZEM_READ_INTERVAL = 1000;  // Baca PZEM setiap 1 detik
const unsigned long MQTT_SEND_INTERVAL = 300000;  // Kirim ke MQTT setiap 5 menit (300000ms)
const unsigned long MQTT_RECONNECT_INTERVAL = 5000;  // Coba koneksi ulang setiap 5 detik

uint8_t address;
bool pzem_data_available = false;
JsonDocument last_pzem_data;

// Variabel untuk data statistik 5 menit
struct PZEMStats {
  float voltage_sum = 0;
  float current_sum = 0;
  float power_sum = 0;
  float energy_sum = 0;
  float voltage_min = 999;
  float voltage_max = 0;
  float current_min = 999;
  float current_max = 0;
  float power_min = 999;
  float power_max = 0;
  int sample_count = 0;
  unsigned long first_timestamp = 0;
  unsigned long last_timestamp = 0;
  
  void reset() {
    voltage_sum = current_sum = power_sum = energy_sum = 0;
    voltage_min = current_min = power_min = 999;
    voltage_max = current_max = power_max = 0;
    sample_count = 0;
    first_timestamp = last_timestamp = 0;
  }
  
  void addSample(JsonDocument& data, unsigned long timestamp) {
    if (sample_count == 0) {
      first_timestamp = timestamp;
    }
    last_timestamp = timestamp;
    
    float voltage = data["voltage"];
    float current = data["current"];
    float power = data["active_power"];
    float energy = data["active_energy"];
    
    // Sum untuk average
    voltage_sum += voltage;
    current_sum += current;
    power_sum += power;
    energy_sum += energy;
    
    // Min/Max tracking
    if (voltage < voltage_min) voltage_min = voltage;
    if (voltage > voltage_max) voltage_max = voltage;
    if (current < current_min) current_min = current;
    if (current > current_max) current_max = current;
    if (power < power_min) power_min = power;
    if (power > power_max) power_max = power;
    
    sample_count++;
  }
};

PZEMStats stats;

// Fungsi untuk setup WiFi
void setupWiFi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

// Callback untuk pesan MQTT yang diterima
void mqttCallback(char* topic, byte* message, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String messageTemp;
  
  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
    messageTemp += (char)message[i];
  }
  Serial.println();
}

// Fungsi untuk koneksi ke MQTT broker
void connectToMQTT() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, cannot connect to MQTT");
    return;
  }
  
  Serial.print("Attempting MQTT connection to ");
  Serial.print(mqtt_server);
  Serial.print(":");
  Serial.print(mqtt_port);
  Serial.print(" as ");
  Serial.print(mqtt_client_id);
  Serial.print("...");
  
  // Set buffer size for larger messages (default is 256 bytes)
  mqtt_client.setBufferSize(2048);
  
  if (mqtt_client.connect(mqtt_client_id)) {
    Serial.println(" connected!");
    
    // Optional: Publish a connection status
    String status_msg = "{\"status\":\"connected\",\"device\":\"" + String(mqtt_client_id) + "\",\"address\":\"" + String(address, HEX) + "\"}";
    mqtt_client.publish("energy/pzem/status", status_msg.c_str());
    
    // Subscribe ke topik jika diperlukan
    // mqtt_client.subscribe("energy/pzem/command");
  } else {
    Serial.print(" failed, rc=");
    Serial.print(mqtt_client.state());
    
    // Print error meaning
    switch (mqtt_client.state()) {
      case -4: Serial.println(" (MQTT_CONNECTION_TIMEOUT)"); break;
      case -3: Serial.println(" (MQTT_CONNECTION_LOST)"); break;
      case -2: Serial.println(" (MQTT_CONNECT_FAILED)"); break;
      case -1: Serial.println(" (MQTT_DISCONNECTED)"); break;
      case 1: Serial.println(" (MQTT_CONNECT_BAD_PROTOCOL)"); break;
      case 2: Serial.println(" (MQTT_CONNECT_BAD_CLIENT_ID)"); break;
      case 3: Serial.println(" (MQTT_CONNECT_UNAVAILABLE)"); break;
      case 4: Serial.println(" (MQTT_CONNECT_BAD_CREDENTIALS)"); break;
      case 5: Serial.println(" (MQTT_CONNECT_UNAUTHORIZED)"); break;
      default: Serial.println(" (Unknown error)"); break;
    }
  }
}

// Fungsi untuk membaca data PZEM secara asinkron
void readPZEMAsync() {
  unsigned long currentMillis = millis();
  
  if (currentMillis - lastPZEMRead >= PZEM_READ_INTERVAL) {
    lastPZEMRead = currentMillis;
    
    if (pzem.read()) {
      // Clear previous data
      last_pzem_data.clear();
      
      // Convert to JSON
      pzem.toJson(last_pzem_data.to<JsonObject>());
      pzem_data_available = true;
      
      // Tambahkan ke statistik
      stats.addSample(last_pzem_data, currentMillis);
      
      // Print ke serial untuk debugging (setiap pembacaan)
      Serial.printf("0x%02X ", address);
      serializeJson(last_pzem_data, Serial);
      Serial.printf(" [Sample: %d/300]\n", stats.sample_count);
      
    } else {
      Serial.println("Failed to read PZEM data");
    }
  }
}

// Fungsi untuk mengirim data via MQTT (setiap 5 menit)
void sendMQTTData() {
  unsigned long currentMillis = millis();
  
  // Cek apakah sudah waktunya mengirim (5 menit)
  if (currentMillis - lastMQTTSend >= MQTT_SEND_INTERVAL && stats.sample_count > 0) {
    lastMQTTSend = currentMillis;
    
    // Debug: Check MQTT connection status
    if (!mqtt_client.connected()) {
      Serial.println("MQTT not connected, cannot send data");
      return;
    }
    
    // Create complete JSON dengan data statistik 5 menit
    JsonDocument mqtt_doc;
    mqtt_doc["device_address"] = String(address, HEX);
    mqtt_doc["timestamp"] = currentMillis;
    mqtt_doc["wifi_rssi"] = WiFi.RSSI();
    mqtt_doc["interval_minutes"] = 5;
    mqtt_doc["sample_count"] = stats.sample_count;
    mqtt_doc["period_start"] = stats.first_timestamp;
    mqtt_doc["period_end"] = stats.last_timestamp;
    
    // Data rata-rata
    mqtt_doc["avg_voltage"] = stats.voltage_sum / stats.sample_count;
    mqtt_doc["avg_current"] = stats.current_sum / stats.sample_count;
    mqtt_doc["avg_power"] = stats.power_sum / stats.sample_count;
    mqtt_doc["total_energy"] = stats.energy_sum / stats.sample_count;
    
    // Data min/max
    mqtt_doc["min_voltage"] = stats.voltage_min;
    mqtt_doc["max_voltage"] = stats.voltage_max;
    mqtt_doc["min_current"] = stats.current_min;
    mqtt_doc["max_current"] = stats.current_max;
    mqtt_doc["min_power"] = stats.power_min;
    mqtt_doc["max_power"] = stats.power_max;
    
    // Data saat ini (snapshot terakhir)
    mqtt_doc["current_data"] = last_pzem_data;
    
    // Serialize to string
    String payload;
    serializeJson(mqtt_doc, payload);
    
    // Debug: Print payload info
    Serial.printf("\n=== SENDING 5-MINUTE SUMMARY ===\n");
    Serial.printf("Samples collected: %d\n", stats.sample_count);
    Serial.printf("Average Power: %.2f W\n", stats.power_sum / stats.sample_count);
    Serial.printf("Payload size: %d bytes\n", payload.length());
    Serial.printf("Sending to topic: %s\n", mqtt_topic);
    
    // Check payload size
    if (payload.length() > 1024) {
      Serial.println("Payload too large, sending simplified data");
      
      // Send simplified 5-minute summary
      JsonDocument simple_doc;
      simple_doc["address"] = address;
      simple_doc["timestamp"] = currentMillis;
      simple_doc["interval_min"] = 5;
      simple_doc["samples"] = stats.sample_count;
      simple_doc["avg_voltage"] = stats.voltage_sum / stats.sample_count;
      simple_doc["avg_current"] = stats.current_sum / stats.sample_count;
      simple_doc["avg_power"] = stats.power_sum / stats.sample_count;
      simple_doc["energy"] = stats.energy_sum / stats.sample_count;
      
      payload = "";
      serializeJson(simple_doc, payload);
    }
    
    // Publish ke MQTT with QoS 0
    if (mqtt_client.publish(mqtt_topic, payload.c_str(), false)) {
      Serial.println("✓ 5-minute summary sent to MQTT successfully");
      Serial.printf("Published: %s\n", payload.c_str());
    } else {
      Serial.println("✗ Failed to send 5-minute summary to MQTT");
      Serial.printf("MQTT State: %d\n", mqtt_client.state());
      Serial.printf("WiFi Status: %d\n", WiFi.status());
      
      // Try to reconnect on next iteration
      lastMQTTReconnect = 0;
    }
    
    // Reset statistik untuk periode berikutnya
    stats.reset();
    Serial.println("Statistics reset for next 5-minute period");
    Serial.println("=====================================\n");
  }
}

// Fungsi untuk handle koneksi MQTT secara asinkron
void handleMQTTConnection() {
  unsigned long currentMillis = millis();
  
  if (!mqtt_client.connected()) {
    if (currentMillis - lastMQTTReconnect >= MQTT_RECONNECT_INTERVAL) {
      lastMQTTReconnect = currentMillis;
      connectToMQTT();
    }
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial)
    continue;

  Serial.println("Starting ESP32 PZEM004Tv3 with MQTT...");
  
  // Initialize PZEM
  pzem.begin(Serial1, 14, 27, 0x02);
  address = pzem.getDeviceAddress();
  
  Serial.printf("PZEM Device Address: 0x%02X\n", address);
  
  // Setup WiFi
  setupWiFi();
  
  // Setup MQTT
  mqtt_client.setServer(mqtt_server, mqtt_port);
  mqtt_client.setCallback(mqttCallback);
  
  // Initial MQTT connection
  connectToMQTT();
  
  Serial.println("Setup completed. Starting main loop...");
}

void loop() {
  // Handle WiFi reconnection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi connection lost. Reconnecting...");
    setupWiFi();
  }
  
  // Handle MQTT connection
  handleMQTTConnection();
  
  // Process MQTT messages
  mqtt_client.loop();
  
  // Read PZEM data asynchronously
  readPZEMAsync();
  
  // Send data via MQTT
  sendMQTTData();
  
  // Small delay to prevent watchdog reset
  delay(10);
}
# PZEM IoT Monitoring System - AI Coding Guidelines

## Architecture Overview
This is an IoT energy monitoring system with ESP32 microcontrollers collecting data from PZEM-004T sensors and sending it via MQTT to a Python backend that stores data in PostgreSQL and serves a real-time web dashboard.

**Data Flow**: PZEM sensors → ESP32 firmware → MQTT broker → Python MQTT client → PostgreSQL → Flask app with SocketIO → Web dashboard

**Key Components**:
- `ESP32-Multi-Pzem-Main/`: PlatformIO firmware for ESP32 data collection
- `pzem-monitoring/`: Python backend with versions V2-V9 showing incremental improvements
- `V9-Docker/`: Production Docker deployment with nginx reverse proxy

## Development Workflows

### ESP32 Firmware
- Build and upload: `pio run --target upload` (from ESP32-Multi-Pzem-Main/)
- Monitor serial: `pio device monitor`
- Configure WiFi/MQTT in `src/main.cpp` (lines 15-25)
- Default MQTT topic: `energy/pzem/data`

### Python Backend
- Install dependencies: `pip install -r requirements.txt`
- Setup database: `psql -U postgres -f database_setup.sql`
- Run full system: `python run_system.py` (starts MQTT client + Flask app)
- Debug MQTT: Check `mqtt_client.log` in V4/ or current version
- Test connections: Run `test_db_connection.py`, `test_mqtt.py`

### Database Schema
Use PostgreSQL with table `pzem_data` containing:
- `device_address` (VARCHAR): Sensor identifier (e.g., "02")
- `timestamp_utc` (TIMESTAMP): UTC timestamp
- `voltage`, `current`, `active_power`, `active_energy` (DECIMAL): Measurements
- Aggregated fields: `avg_voltage`, `min_voltage`, `max_voltage`, etc.

## Code Patterns

### MQTT Message Format
ESP32 sends JSON like:
```json
{
  "device_address": "02",
  "timestamp": 1704067200,
  "avg_voltage": 220.5,
  "total_energy_kwh": 0.042,
  "energy_method": "counter_delta"
}
```

### Database Queries
Use parameterized queries with `psycopg2.extras.RealDictCursor`:
```python
cursor.execute("""
    SELECT * FROM pzem_data 
    WHERE device_address = %s 
    ORDER BY timestamp_utc DESC LIMIT %s
""", (device_address, limit))
```

### Version Organization
Each version (V2-V9) in separate subfolder with:
- Incremental features (e.g., V8 adds reporting, V9 adds Docker)
- `README.md` documenting changes
- Migration scripts (e.g., `migrate_database.py`)

### Error Handling
- Database: Reconnect on failure with exponential backoff
- MQTT: Auto-reconnect with `on_disconnect` callback
- Logging: Use `logging` module with file + console handlers

## Integration Points

### External Dependencies
- MQTT Broker: `103.87.67.139:1883` (Mosquitto)
- PostgreSQL: Local or Docker container
- WebSocket: Flask-SocketIO for real-time dashboard updates

### Configuration
- Database: `DB_CONFIG` dict in Python files
- MQTT: Constants at top of `mqtt_client_improved.py`
- Flask: `app.config['SECRET_KEY']` and CORS settings

## Key Files to Reference
- `ESP32-Multi-Pzem-Main/src/main.cpp`: Firmware logic and MQTT publishing
- `pzem-monitoring/V4/mqtt_client_improved.py`: MQTT subscription and data storage
- `pzem-monitoring/app.py`: Dashboard API and real-time updates
- `V9-Docker/docker-compose.yml`: Production deployment setup</content>
<parameter name="filePath">c:\Users\info\Documents\Project\not-released\IoT-Project\PZEM-Project\.github\copilot-instructions.md
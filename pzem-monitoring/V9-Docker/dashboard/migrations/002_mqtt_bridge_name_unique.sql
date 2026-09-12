-- Nama tunnel MQTT bridge harus unik agar canvas bisa merujuk dengan naming.
CREATE UNIQUE INDEX IF NOT EXISTS idx_mqtt_bridge_configs_name_unique ON mqtt_bridge_configs (name);

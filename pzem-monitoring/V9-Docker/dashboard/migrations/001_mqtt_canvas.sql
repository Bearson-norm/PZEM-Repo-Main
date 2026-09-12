-- MQTT bridge configs and canvas definitions; extend pzem_data traceability

CREATE TABLE IF NOT EXISTS mqtt_bridge_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    broker_host VARCHAR(255) NOT NULL,
    broker_port INTEGER NOT NULL DEFAULT 1883,
    use_tls BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(120),
    password_enc TEXT,
    topics JSONB NOT NULL DEFAULT '[]'::jsonb,
    qos SMALLINT NOT NULL DEFAULT 1,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_connect_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS canvas_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    poll_interval_seconds INTEGER DEFAULT 300,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_canvas_definitions_enabled ON canvas_definitions (enabled);
CREATE INDEX IF NOT EXISTS idx_mqtt_bridge_configs_enabled ON mqtt_bridge_configs (enabled);

-- Link readings to bridge (nullable for legacy mqtt_listener rows)
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS mqtt_bridge_config_id INTEGER REFERENCES mqtt_bridge_configs(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_pzem_data_bridge_created ON pzem_data (mqtt_bridge_config_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pzem_data_device_created ON pzem_data (device_address, created_at DESC);

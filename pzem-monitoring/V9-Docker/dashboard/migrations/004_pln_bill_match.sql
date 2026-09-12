-- PLN bill matching: meter-register series, events, heartbeat, readings, reconciliations.
-- Idempotent. Safe to re-run.

ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS building VARCHAR(100);
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS phase VARCHAR(8);
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS device_id VARCHAR(64);
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS firmware_version VARCHAR(32);
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS time_synced BOOLEAN;
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS timestamp_unix BIGINT;
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS period_start_unix BIGINT;
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS period_end_unix BIGINT;
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS period_duration_ms BIGINT;
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS is_retry BOOLEAN;
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS meter_energy_kwh NUMERIC(14, 4);
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS energy_first NUMERIC(14, 4);
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS energy_last NUMERIC(14, 4);
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS accumulated_energy_kwh NUMERIC(14, 4);
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS energy_method VARCHAR(32);
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS energy_event VARCHAR(16);
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS payload_json JSONB;
ALTER TABLE pzem_data ADD COLUMN IF NOT EXISTS payload_hash TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_pzem_data_payload_hash
    ON pzem_data (payload_hash)
    WHERE payload_hash IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_pzem_data_synced_period
    ON pzem_data (building, phase, period_end_unix)
    WHERE time_synced = TRUE AND period_end_unix > 0
      AND building IS NOT NULL AND phase IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pzem_data_bill_lookup
    ON pzem_data (building, phase, period_end_unix)
    WHERE time_synced = TRUE AND period_end_unix > 0;

CREATE TABLE IF NOT EXISTS pzem_energy_events (
    id SERIAL PRIMARY KEY,
    building VARCHAR(100) NOT NULL,
    phase VARCHAR(8) NOT NULL,
    event_type VARCHAR(16) NOT NULL,
    period_end_unix BIGINT,
    meter_energy_kwh NUMERIC(14, 4),
    source_payload_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_pzem_energy_events_hash_type
    ON pzem_energy_events (source_payload_hash, event_type)
    WHERE source_payload_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pzem_energy_events_lookup
    ON pzem_energy_events (building, phase, period_end_unix);

CREATE TABLE IF NOT EXISTS pzem_device_heartbeat (
    building VARCHAR(100) NOT NULL,
    phase VARCHAR(8) NOT NULL,
    device_address VARCHAR(64),
    pzem_connected BOOLEAN,
    buffer_count INTEGER,
    pzem_read_errors INTEGER,
    seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    payload_json JSONB,
    PRIMARY KEY (building, phase)
);

CREATE TABLE IF NOT EXISTS pln_readings (
    id SERIAL PRIMARY KEY,
    building VARCHAR(100) NOT NULL,
    read_at TIMESTAMPTZ NOT NULL,
    pln_register_kwh NUMERIC(14, 4) NOT NULL,
    invoice_kwh NUMERIC(14, 4),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pln_readings_building_at
    ON pln_readings (building, read_at);

CREATE TABLE IF NOT EXISTS pln_reconciliations (
    id SERIAL PRIMARY KEY,
    building VARCHAR(100) NOT NULL,
    t0_reading_id INTEGER NOT NULL REFERENCES pln_readings(id) ON DELETE CASCADE,
    t1_reading_id INTEGER NOT NULL REFERENCES pln_readings(id) ON DELETE CASCADE,
    quality VARCHAR(20) NOT NULL,
    total_kwh NUMERIC(14, 4),
    invoice_kwh NUMERIC(14, 4),
    error_pct NUMERIC(10, 4),
    meter_sum_t0 NUMERIC(14, 4),
    meter_sum_t1 NUMERIC(14, 4),
    pln_register_t0 NUMERIC(14, 4),
    pln_register_t1 NUMERIC(14, 4),
    offset_t0 NUMERIC(14, 4),
    offset_t1 NUMERIC(14, 4),
    phases_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    flags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (t0_reading_id, t1_reading_id)
);

CREATE INDEX IF NOT EXISTS idx_pln_reconciliations_building
    ON pln_reconciliations (building, created_at DESC);

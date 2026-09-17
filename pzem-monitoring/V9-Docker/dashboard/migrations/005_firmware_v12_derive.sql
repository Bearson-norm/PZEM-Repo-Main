-- Firmware v1.2.0: persist calibration used to derive window kWh on ingest.
-- Idempotent. Safe to re-run.

ALTER TABLE pzem_data
    ADD COLUMN IF NOT EXISTS energy_scale NUMERIC(14, 6),
    ADD COLUMN IF NOT EXISTS energy_offset NUMERIC(14, 6);

-- Pengaturan tarif PLN (single-row, dapat diubah dari UI)
CREATE TABLE IF NOT EXISTS pln_tariff_settings (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    tariff_class VARCHAR(10) NOT NULL DEFAULT 'B2',
    contracted_va INTEGER,
    ppn_percent NUMERIC(6, 4) NOT NULL DEFAULT 0.11,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO pln_tariff_settings (id, tariff_class, contracted_va, ppn_percent)
VALUES (1, 'B2', 53000, 0.11)
ON CONFLICT (id) DO NOTHING;

# Panduan Export Database PostgreSQL PZEM Monitoring

Script ini membantu Anda untuk mengekspor semua data dari database PostgreSQL yang digunakan oleh sistem PZEM Monitoring.

## Persyaratan

- Python 3.6 atau lebih baru
- Library `psycopg2` (PostgreSQL adapter untuk Python)
- Akses ke database PostgreSQL

### Install Dependencies

```bash
pip install psycopg2-binary
```

## Konfigurasi Database

Script menggunakan environment variables atau command line arguments untuk konfigurasi database:

### Environment Variables (Recommended)

```bash
# Windows (PowerShell)
$env:DB_HOST="localhost"
$env:DB_NAME="pzem_monitoring"
$env:DB_USER="postgres"
$env:DB_PASS="Admin123"
$env:DB_PORT="5432"

# Windows (CMD)
set DB_HOST=localhost
set DB_NAME=pzem_monitoring
set DB_USER=postgres
set DB_PASS=Admin123
set DB_PORT=5432

# Linux/Mac
export DB_HOST=localhost
export DB_NAME=pzem_monitoring
export DB_USER=postgres
export DB_PASS=Admin123
export DB_PORT=5432
```

### Default Configuration

Jika tidak ada environment variables, script akan menggunakan default:
- Host: `localhost`
- Database: `pzem_monitoring`
- User: `postgres`
- Password: `Admin123`
- Port: `5432`

## Cara Penggunaan

### 1. Lihat Summary Database (Tidak Export)

```bash
python export_database.py --summary
```

Ini akan menampilkan:
- Daftar tabel
- Jumlah baris per tabel
- Struktur kolom setiap tabel

### 2. Export ke SQL (Recommended untuk Backup)

```bash
# Auto-generate filename
python export_database.py --format sql

# Custom filename
python export_database.py --format sql --output backup_20250101.sql
```

File SQL dapat di-restore dengan:
```bash
psql -U postgres -d pzem_monitoring < backup.sql
```

### 3. Export ke CSV (Untuk Analisis di Excel)

```bash
# Auto-generate directory
python export_database.py --format csv

# Custom directory
python export_database.py --format csv --output exports/
```

Setiap tabel akan diekspor ke file CSV terpisah:
- `pzem_data.csv`
- `pzem_devices.csv`

### 4. Export ke JSON (Untuk Program/API)

```bash
# Auto-generate filename
python export_database.py --format json

# Custom filename
python export_database.py --format json --output backup.json
```

### 5. Export Semua Format

```bash
python export_database.py --format all
```

Ini akan membuat:
- File SQL backup
- Directory dengan file CSV per tabel
- File JSON dengan semua data

### 6. Custom Database Connection

```bash
python export_database.py \
  --host 192.168.1.100 \
  --db my_database \
  --user my_user \
  --pass my_password \
  --port 5432 \
  --format all
```

### 7. Menggunakan Batch File (Windows)

```cmd
# Export semua format
export_database.bat

# Export format tertentu
export_database.bat sql
export_database.bat csv exports/
export_database.bat json backup.json
```

**Catatan:** Edit `export_database.bat` untuk mengubah konfigurasi database jika diperlukan.

## Contoh Output

### Summary Output

```
============================================================
DATABASE SUMMARY
============================================================
Database: pzem_monitoring
Host: localhost
User: postgres

Table: pzem_data
  Rows: 125,430
  Columns: 16
    - id: integer
    - device_address: character varying
    - voltage: numeric
    - current: numeric
    - power: numeric
    - energy: numeric
    ...

Table: pzem_devices
  Rows: 3
  Columns: 11
    - device_address: character varying
    - device_name: character varying
    ...

Total Tables: 2
Total Rows: 125,433
============================================================
```

### Export Progress

```
📄 Exporting ke SQL: pzem_backup_20250101_120000.sql
  → Exporting table: pzem_data
    Rows: 125,430
    Exported 10,000 rows...
    Exported 20,000 rows...
    ✓ Completed: 125,430 rows exported
  → Exporting table: pzem_devices
    Rows: 3
    ✓ Completed: 3 rows exported

✓ SQL export completed: pzem_backup_20250101_120000.sql
```

## Troubleshooting

### Error: "connection to server failed"

**Penyebab:** Database tidak dapat diakses

**Solusi:**
1. Pastikan PostgreSQL server sedang berjalan
2. Cek host, port, dan firewall settings
3. Verifikasi kredensial database

```bash
# Test connection dengan psql
psql -h localhost -U postgres -d pzem_monitoring
```

### Error: "module 'psycopg2' not found"

**Penyebab:** Library psycopg2 belum terinstall

**Solusi:**
```bash
pip install psycopg2-binary
```

### Error: "permission denied"

**Penyebab:** User database tidak memiliki akses read

**Solusi:**
1. Pastikan user memiliki SELECT permission
2. Hubungi database administrator

### File Export Terlalu Besar

Jika database sangat besar (>1GB), gunakan:

1. **Export per tabel:**
   - Edit script untuk export satu tabel pada satu waktu
   
2. **Export dengan filter tanggal:**
   - Modifikasi query untuk hanya export data tertentu:
   ```sql
   SELECT * FROM pzem_data 
   WHERE created_at >= '2024-01-01' 
   ORDER BY id;
   ```

3. **Gunakan pg_dump (PostgreSQL native):**
   ```bash
   pg_dump -U postgres -d pzem_monitoring > backup.sql
   ```

## Restore Database dari SQL Backup

### Full Restore

```bash
# Drop dan recreate database (HATI-HATI!)
psql -U postgres -c "DROP DATABASE IF EXISTS pzem_monitoring;"
psql -U postgres -c "CREATE DATABASE pzem_monitoring;"

# Restore
psql -U postgres -d pzem_monitoring < backup.sql
```

### Restore ke Database Baru

```bash
# Create database baru
psql -U postgres -c "CREATE DATABASE pzem_monitoring_backup;"

# Restore
psql -U postgres -d pzem_monitoring_backup < backup.sql
```

## Tips

1. **Backup Regular:** Buat backup secara berkala (harian/mingguan)
2. **Compress Files:** Gunakan gzip atau 7zip untuk mengompres file backup
3. **Verify Backup:** Setelah export, test restore ke database test
4. **Multiple Formats:** Export ke beberapa format untuk fleksibilitas
5. **Documentation:** Simpan dokumentasi tentang kapan dan bagaimana backup dibuat

## Support

Jika ada masalah atau pertanyaan, silakan:
1. Cek log error dengan detail
2. Verifikasi konfigurasi database
3. Pastikan semua dependencies terinstall

## License

Script ini bagian dari proyek PZEM Monitoring System.




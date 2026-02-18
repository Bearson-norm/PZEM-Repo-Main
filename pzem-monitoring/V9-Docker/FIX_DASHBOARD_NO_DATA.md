# Fix: Dashboard Tidak Menampilkan Data Setelah 2-3 Hari

## Masalah
Dashboard v9-dashboard berhenti menampilkan data setelah berjalan sekitar 2-3 hari, meskipun MQTT listener masih bekerja dengan baik. Solusi sementara adalah restart Docker container.

## Penyebab Masalah
Setelah analisis kode, ditemukan beberapa masalah potensial:

1. **WebSocket Connection Timeout**: Tidak ada mekanisme automatic reconnection untuk Socket.IO
2. **Database Connection Pool Exhaustion**: Koneksi database tidak di-cleanup dengan baik setelah idle
3. **Connection Timeout**: PostgreSQL connection timeout tidak di-handle dengan baik
4. **Tidak Ada Health Check**: Tidak ada mekanisme periodic health check dan recovery
5. **Error Accumulation**: Error yang terjadi tidak di-handle dengan baik dan bisa menyebabkan crash

## Perbaikan yang Dilakukan

### 1. Automatic WebSocket Reconnection (Frontend)
**File**: `dashboard/templates/dashboard.html`

- ✅ Menambahkan automatic reconnection dengan exponential backoff
- ✅ Menambahkan event handlers untuk `connect_error`, `reconnect`, `reconnect_attempt`, `reconnect_failed`
- ✅ Menambahkan periodic data update check (setiap 30 detik)
- ✅ Fallback ke REST API jika WebSocket tidak menerima data selama 2+ menit
- ✅ Logging yang lebih baik untuk debugging

**Fitur Baru**:
- Reconnection dengan delay: 1s → 2s → 4s → ... → max 30s
- Automatic API fallback jika WebSocket tidak menerima data
- Tracking waktu data terakhir diterima

### 2. Database Connection Pool Improvements (Backend)
**File**: `dashboard/app_with_reporting.py`

- ✅ Menambahkan connection timeout settings (10 detik)
- ✅ Menambahkan PostgreSQL keepalive settings:
  - `keepalives_idle`: 30 detik
  - `keepalives_interval`: 10 detik
  - `keepalives_count`: 3
- ✅ Menambahkan statement timeout (30 detik) untuk mencegah long-running queries
- ✅ Improved error handling dengan reconnection otomatis

### 3. Periodic Health Check
**File**: `dashboard/app_with_reporting.py`

- ✅ Menambahkan `_perform_health_check()` method
- ✅ Health check setiap 5 menit
- ✅ Automatic reconnection jika health check gagal
- ✅ Health check juga dilakukan di background thread

### 4. Enhanced Error Recovery
**File**: `dashboard/app_with_reporting.py`

- ✅ Menambahkan consecutive error tracking
- ✅ Automatic recovery setelah 5 error berturut-turut
- ✅ Database reconnection otomatis pada error
- ✅ Better error logging dengan traceback

### 5. Background Thread Improvements
**File**: `dashboard/app_with_reporting.py`

- ✅ Menambahkan error recovery mechanism
- ✅ Consecutive error tracking dengan max limit
- ✅ Automatic database reconnection pada error
- ✅ Health check integration

## Cara Testing

### 1. Test WebSocket Reconnection
1. Buka dashboard di browser
2. Stop dashboard container: `docker-compose stop dashboard`
3. Tunggu beberapa detik
4. Start kembali: `docker-compose start dashboard`
5. Dashboard seharusnya otomatis reconnect dan menampilkan data

### 2. Test Database Connection Recovery
1. Monitor logs: `docker-compose logs -f dashboard`
2. Simulasi database error dengan menghentikan sementara database
3. Dashboard seharusnya otomatis reconnect ketika database kembali online

### 3. Test Long-Running Stability
1. Biarkan dashboard berjalan selama beberapa hari
2. Monitor memory usage dan connection count
3. Dashboard seharusnya tetap stabil tanpa perlu restart

## Monitoring

### Check Logs
```bash
# Dashboard logs
docker-compose logs -f dashboard

# MQTT listener logs
docker-compose logs -f mqtt-listener

# Database logs
docker-compose logs -f db
```

### Check Health Status
Akses endpoint: `http://your-server:5000/health`

Response akan menunjukkan:
- Database connection status
- System info
- Three-phase summary

### Check WebSocket Connection
Di browser console, cek:
- `socket.connected` - harus `true`
- Log messages menunjukkan reconnection attempts jika ada

## Troubleshooting

### Jika Masih Ada Masalah

1. **Check Database Connections**:
   ```sql
   SELECT count(*) FROM pg_stat_activity WHERE datname = 'pzem_monitoring';
   ```

2. **Check Memory Usage**:
   ```bash
   docker stats
   ```

3. **Check Logs untuk Error Patterns**:
   ```bash
   docker-compose logs dashboard | grep ERROR
   ```

4. **Manual Restart jika Diperlukan**:
   ```bash
   docker-compose restart dashboard
   ```

## Catatan Penting

- Health check berjalan setiap 5 menit
- WebSocket reconnection menggunakan exponential backoff
- API fallback aktif jika tidak ada data selama 2+ menit
- Database connection timeout: 10 detik
- Statement timeout: 30 detik
- Keepalive settings mencegah connection timeout

## Update History

- **2024-01-XX**: Initial fix untuk masalah dashboard tidak menampilkan data setelah 2-3 hari
  - Automatic WebSocket reconnection
  - Database connection pool improvements
  - Periodic health checks
  - Enhanced error recovery

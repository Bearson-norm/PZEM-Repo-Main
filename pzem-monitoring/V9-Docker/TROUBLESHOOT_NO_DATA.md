# 🔍 Troubleshooting: Data Tidak Masuk di Dashboard

## Masalah
Dashboard tidak menampilkan data di localhost.

## Langkah Troubleshooting

### 1. Buka Browser Console (F12)

Buka Developer Tools (F12) dan cek tab **Console** untuk melihat error atau log debug.

**Cara buka:**
- Chrome/Edge: `F12` atau `Ctrl+Shift+I`
- Firefox: `F12` atau `Ctrl+Shift+K`
- Safari: `Cmd+Option+I` (Mac)

### 2. Cek Debug Panel di Dashboard

Dashboard memiliki debug panel yang bisa dibuka dengan tombol di pojok kanan bawah. Cek log untuk melihat:
- ✅ API calls yang berhasil
- ❌ Error yang terjadi
- ⚠️ Warning messages

### 3. Cek API Endpoints

Test apakah API endpoints berfungsi dengan membuka URL berikut di browser:

#### a. System Status
```
http://localhost:5000/api/system-status
```
**Expected:** JSON dengan `total_devices`, `online_devices`, dll.

#### b. Devices List
```
http://localhost:5000/api/devices
```
**Expected:** Array of devices dengan `device_address`, `device_name`, `location`, dll.

#### c. Latest Data
```
http://localhost:5000/api/all-latest
```
**Expected:** Object dengan device addresses sebagai keys dan data sebagai values.

#### d. Chart Data (contoh)
```
http://localhost:5000/api/chart/{device_address}?period=hour
```
**Expected:** Array of data points dengan `time_period`, `voltage`, `current`, `power`, dll.

### 4. Cek Backend Logs

#### Jika menggunakan Docker:
```bash
cd /path/to/pzem-monitoring/V9-Docker
docker-compose logs dashboard --tail=50
```

#### Jika running langsung:
```bash
# Cek logs Flask application
tail -f /path/to/logs/dashboard.log
```

**Cari error seperti:**
- ❌ `Connection refused` → Database tidak running
- ❌ `ModuleNotFoundError` → Dependencies tidak terinstall
- ❌ `Table does not exist` → Database schema belum dibuat
- ❌ `Connection timeout` → Database tidak accessible

### 5. Cek Database Connection

#### Test koneksi database:
```bash
# Masuk ke container database
docker-compose exec db psql -U postgres -d pzem_monitoring

# Atau jika running langsung
psql -U postgres -d pzem_monitoring

# Cek apakah ada data
SELECT COUNT(*) FROM pzem_data;
SELECT COUNT(*) FROM pzem_devices;

# Cek latest data
SELECT * FROM pzem_data ORDER BY created_at DESC LIMIT 10;
```

**Expected:** Harus ada data di tabel `pzem_data` dan `pzem_devices`.

### 6. Cek MQTT Listener

Pastikan MQTT listener berjalan dan menerima data:

```bash
# Cek logs MQTT listener
docker-compose logs mqtt-listener --tail=50

# Cek apakah container running
docker-compose ps mqtt-listener
```

**Expected:** Logs menunjukkan data diterima dari MQTT dan disimpan ke database.

### 7. Cek Network Requests di Browser

1. Buka **Network** tab di Developer Tools (F12)
2. Refresh halaman dashboard
3. Filter untuk `api/` requests
4. Cek setiap request:
   - **Status:** Harus `200 OK`
   - **Response:** Harus berisi data JSON
   - **Time:** Tidak terlalu lama (< 1 detik)

**Jika ada error:**
- `404 Not Found` → API endpoint tidak ada
- `500 Internal Server Error` → Backend error (cek logs)
- `CORS error` → Cross-origin issue
- `Network error` → Server tidak running atau tidak accessible

### 8. Cek Socket.IO Connection

Dashboard menggunakan Socket.IO untuk real-time updates. Cek apakah connection berhasil:

1. Buka **Console** tab
2. Cari log: `Socket.IO connected` atau `Socket.IO disconnected`
3. Cek **Network** tab untuk WebSocket connection (`ws://` atau `wss://`)

**Jika disconnected:**
- Cek apakah Flask-SocketIO berjalan
- Cek firewall/network settings
- Cek browser console untuk error

### 9. Common Issues & Solutions

#### Issue 1: API Returns Empty Array/Object

**Penyebab:** Database kosong atau query tidak menemukan data.

**Solusi:**
```bash
# Cek apakah ada data di database
docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT COUNT(*) FROM pzem_data;"

# Jika kosong, cek apakah MQTT listener menerima data
docker-compose logs mqtt-listener --tail=100 | grep -i "saved\|inserted\|error"
```

#### Issue 2: CORS Error

**Penyebab:** Browser memblokir request karena CORS policy.

**Solusi:**
- Pastikan dashboard dan API di domain/port yang sama
- Atau tambahkan CORS headers di Flask backend

#### Issue 3: JavaScript Errors

**Penyebab:** Error di JavaScript code yang mencegah data loading.

**Solusi:**
- Cek browser console untuk error
- Fix error tersebut
- Refresh halaman

#### Issue 4: Database Connection Error

**Penyebab:** Database tidak running atau credentials salah.

**Solusi:**
```bash
# Restart database
docker-compose restart db

# Cek connection
docker-compose exec db psql -U postgres -d pzem_monitoring -c "SELECT 1;"
```

#### Issue 5: Port Already in Use

**Penyebab:** Port 5000 sudah digunakan oleh process lain.

**Solusi:**
```bash
# Cek process yang menggunakan port 5000
sudo lsof -i :5000
# atau
sudo netstat -tlnp | grep 5000

# Kill process tersebut atau ubah port di docker-compose.yml
```

### 10. Manual Test dengan curl

Test API endpoints dari command line:

```bash
# System status
curl http://localhost:5000/api/system-status

# Devices
curl http://localhost:5000/api/devices

# Latest data
curl http://localhost:5000/api/all-latest

# Chart data (ganti {device_address} dengan actual address)
curl "http://localhost:5000/api/chart/{device_address}?period=hour"
```

**Expected:** Semua command harus return JSON data tanpa error.

### 11. Check File Permissions

Pastikan file dashboard.html bisa diakses:

```bash
# Cek permission
ls -la dashboard/templates/dashboard.html

# Jika perlu, fix permission
chmod 644 dashboard/templates/dashboard.html
```

### 12. Clear Browser Cache

Browser cache bisa menyebabkan masalah:

1. **Chrome/Edge:** `Ctrl+Shift+Delete` → Clear cache
2. **Firefox:** `Ctrl+Shift+Delete` → Clear cache
3. Atau gunakan **Incognito/Private mode** untuk test

### 13. Check Flask Application Logs

Jika running langsung (bukan Docker), cek Flask logs:

```bash
# Jika menggunakan gunicorn
tail -f /var/log/gunicorn/error.log

# Jika running dengan python langsung
# Cek terminal dimana Flask app running
```

## Quick Fix Checklist

- [ ] Dashboard container running? → `docker-compose ps dashboard`
- [ ] Database container running? → `docker-compose ps db`
- [ ] MQTT listener running? → `docker-compose ps mqtt-listener`
- [ ] API endpoints accessible? → Test dengan curl atau browser
- [ ] Database has data? → Check dengan psql
- [ ] No JavaScript errors? → Check browser console
- [ ] Socket.IO connected? → Check browser console
- [ ] Browser cache cleared? → Clear cache atau use incognito

## Debug Mode

Dashboard memiliki debug mode yang bisa diaktifkan:

1. Buka dashboard di browser
2. Klik tombol debug di pojok kanan bawah
3. Cek log untuk melihat:
   - API calls
   - Data received
   - Errors
   - Warnings

## Still Not Working?

Jika semua langkah di atas sudah dilakukan tapi masih tidak ada data:

1. **Collect Information:**
   - Browser console logs (screenshot)
   - Network tab (screenshot)
   - Backend logs (last 100 lines)
   - Database query results

2. **Check:**
   - Apakah ada data di database?
   - Apakah API endpoints return data?
   - Apakah ada error di logs?

3. **Report:**
   - Share logs dan screenshots
   - Describe steps yang sudah dilakukan
   - Mention browser dan OS version

---

**Catatan:** Pastikan semua services (db, dashboard, mqtt-listener) running dan tidak ada error di logs sebelum troubleshooting lebih lanjut.

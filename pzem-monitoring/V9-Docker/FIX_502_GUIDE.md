# Panduan Perbaikan 502 Bad Gateway

## Masalah
Error 502 Bad Gateway terjadi ketika Nginx tidak bisa terhubung ke Flask dashboard container. Error ini biasanya muncul karena:
1. Dashboard container tidak berjalan
2. Dashboard container crash/error
3. Nginx configuration salah
4. Port 5000 tidak accessible
5. WebSocket/Socket.IO configuration tidak lengkap

## Solusi Cepat

### Opsi 1: Menggunakan Script Otomatis (Recommended)

```bash
# SSH ke VPS
ssh foom@your-vps-ip

# Masuk ke direktori project
cd /opt/pzem-monitoring

# Berikan permission execute
chmod +x FIX_502_VPS.sh

# Jalankan script
./FIX_502_VPS.sh
```

Script ini akan:
- ✅ Memeriksa dan restart dashboard container
- ✅ Memverifikasi dashboard accessible di localhost:5000
- ✅ Memeriksa Nginx configuration
- ✅ Reload Nginx
- ✅ Melakukan final verification

### Opsi 2: Perbaikan Manual

#### Langkah 1: Cek Status Container

```bash
cd /opt/pzem-monitoring
docker-compose ps
```

Pastikan semua container berstatus `Up`, terutama `dashboard`.

#### Langkah 2: Restart Dashboard Container

```bash
docker-compose restart dashboard
# Tunggu 10-15 detik
sleep 15
```

#### Langkah 3: Cek Dashboard Logs

```bash
docker-compose logs dashboard --tail=50
```

Cari error seperti:
- `Error getting system status`
- `Database connection error`
- `Port already in use`
- `Module not found`

#### Langkah 4: Test Dashboard Accessibility

```bash
curl http://localhost:5000/health
```

Harus mengembalikan JSON response seperti:
```json
{"status": "ok", "timestamp": "..."}
```

Jika tidak, dashboard container mungkin crash atau error.

#### Langkah 5: Cek Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/pzem.moof-set.web.id
```

Pastikan ada konfigurasi seperti ini:

```nginx
server {
    listen 80;
    server_name pzem.moof-set.web.id;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support untuk Socket.IO
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}
```

#### Langkah 6: Test Nginx Configuration

```bash
sudo nginx -t
```

Harus mengembalikan:
```
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

#### Langkah 7: Reload Nginx

```bash
sudo systemctl reload nginx
```

Atau jika reload gagal:
```bash
sudo systemctl restart nginx
```

#### Langkah 8: Verifikasi

```bash
# Test dashboard langsung
curl http://localhost:5000/health

# Test melalui Nginx
curl http://pzem.moof-set.web.id/health
# atau
curl https://pzem.moof-set.web.id/health
```

## Troubleshooting Lanjutan

### Masalah 1: Dashboard Container Crash

**Gejala:**
- Container status `Exited` atau `Restarting`
- Logs menunjukkan error

**Solusi:**
```bash
# Cek logs untuk error
docker-compose logs dashboard --tail=100

# Cek apakah ada masalah dengan database connection
docker-compose logs db --tail=50

# Restart semua services
docker-compose down
docker-compose up -d
```

### Masalah 2: Port 5000 Tidak Accessible

**Gejala:**
- `curl http://localhost:5000/health` gagal
- Container running tapi port tidak listen

**Solusi:**
```bash
# Cek apakah port 5000 digunakan
netstat -tuln | grep 5000
# atau
ss -tuln | grep 5000

# Cek docker-compose.yml, pastikan ports mapping benar:
# ports:
#   - "5000:5000"

# Restart container
docker-compose restart dashboard
```

### Masalah 3: Nginx Config Error

**Gejala:**
- `sudo nginx -t` gagal
- Nginx tidak bisa reload

**Solusi:**
```bash
# Backup config lama
sudo cp /etc/nginx/sites-available/pzem.moof-set.web.id /etc/nginx/sites-available/pzem.moof-set.web.id.backup

# Gunakan config example
sudo cp /opt/pzem-monitoring/V9-Docker/nginx-config-example.conf /etc/nginx/sites-available/pzem.moof-set.web.id

# Edit sesuai kebutuhan (domain, SSL, dll)
sudo nano /etc/nginx/sites-available/pzem.moof-set.web.id

# Test dan reload
sudo nginx -t
sudo systemctl reload nginx
```

### Masalah 4: Socket.IO Connection Failed

**Gejala:**
- Browser console menunjukkan error Socket.IO 502
- Real-time updates tidak bekerja

**Solusi:**
Pastikan Nginx config memiliki block `/socket.io/` seperti di Langkah 5.

Jika sudah ada tapi masih error, coba:
```bash
# Pastikan WebSocket headers benar
sudo nano /etc/nginx/sites-available/pzem.moof-set.web.id

# Pastikan ada:
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";

# Reload Nginx
sudo systemctl reload nginx
```

### Masalah 5: Database Connection Error

**Gejala:**
- Dashboard logs menunjukkan database error
- API endpoints return 500 error

**Solusi:**
```bash
# Cek database container
docker-compose ps db

# Cek database logs
docker-compose logs db --tail=50

# Test database connection dari dashboard container
docker-compose exec dashboard python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='db',
        database='pzem_monitoring',
        user='postgres',
        password='Admin123'
    )
    print('✅ Database connection OK')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"
```

## Verifikasi Setelah Perbaikan

1. **Dashboard Health Check:**
   ```bash
   curl http://localhost:5000/health
   ```

2. **API Endpoints:**
   ```bash
   curl http://localhost:5000/api/system-status
   curl http://localhost:5000/api/devices
   ```

3. **Website Access:**
   - Buka browser: `https://pzem.moof-set.web.id/`
   - Clear cache (Ctrl+Shift+R)
   - Cek browser console untuk error

4. **Socket.IO Connection:**
   - Buka browser console
   - Harus melihat: `Connected to server`
   - Tidak ada error 502 untuk `/socket.io/`

## Monitoring

Untuk monitoring real-time:

```bash
# Watch dashboard logs
docker-compose logs -f dashboard

# Watch Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Watch container status
watch -n 2 'docker-compose ps'
```

## Kontak Support

Jika masalah masih berlanjut setelah mengikuti panduan ini:
1. Kumpulkan informasi:
   - Output dari `docker-compose ps`
   - Output dari `docker-compose logs dashboard --tail=100`
   - Output dari `sudo tail -50 /var/log/nginx/error.log`
   - Output dari `curl http://localhost:5000/health`
2. Buat issue dengan informasi tersebut

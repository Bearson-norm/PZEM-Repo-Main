# Prompt Template: Konfigurasi CI/CD untuk Repository Baru

## 📋 Informasi yang Diperlukan

Gunakan prompt ini ketika ingin mengkonfigurasi CI/CD untuk repository baru dengan pengaturan yang berbeda.

---

## 🎯 PROMPT UNTUK AI ASSISTANT

```
Saya ingin mengkonfigurasi CI/CD untuk repository [NAMA_REPOSITORY] dengan spesifikasi berikut:

### Informasi Repository:
- **Nama Repository**: [NAMA_REPOSITORY]
- **Branch Utama**: [main/master/develop]
- **Path Project di Repository**: [contoh: apps/my-app/V1 atau project-folder]

### Informasi VPS:
- **VPS User**: [contoh: deploy, admin, user]
- **VPS Host/IP**: [contoh: 192.168.1.100 atau vps.example.com]
- **Deploy Directory di VPS**: [contoh: /opt/my-app atau /home/user/project]

### Informasi Network & Ports:
- **Dashboard Port**: [contoh: 5000, 8080, 3000]
- **Domain** (jika ada): [contoh: app.example.com atau subdomain.example.com]
- **Health Check Endpoint**: [contoh: /health atau /api/health]

### Informasi SSH:
- **SSH Key Path** (Windows): [contoh: C:\Users\username\.ssh\my_key]
- **SSH Key Path** (Linux/Mac): [contoh: ~/.ssh/my_key]

### Informasi Database (jika berbeda):
- **Database Name**: [contoh: my_app_db]
- **Database User**: [contoh: postgres, admin]
- **Database Password**: [CONTOH_PASSWORD] (akan di-set sebagai GitHub Secret)

### Konfigurasi Tambahan:
- **Docker Compose File Location**: [contoh: root, atau subfolder/docker-compose.yml]
- **Service Names di Docker Compose**: 
  - Dashboard: [contoh: dashboard, app, web]
  - MQTT/Worker: [contoh: mqtt-listener, worker, background]
  - Database: [contoh: db, postgres, database]
- **Backup Location**: [contoh: ~/.app-backups atau /var/backups]

### Fitur yang Diinginkan:
- [ ] CI Pipeline (testing, linting, build)
- [ ] CD Pipeline (deploy otomatis)
- [ ] Security Scanning
- [ ] Database Backup sebelum deploy
- [ ] Health Check setelah deploy
- [ ] Rollback mechanism

### Konfigurasi Khusus:
[Tambahkan konfigurasi khusus lainnya yang diperlukan]

---

Tolong buatkan:
1. File workflow CI/CD (`.github/workflows/ci.yml` dan `deploy.yml`) yang sudah disesuaikan
2. Script setup GitHub Secrets (`.github/setup-github-secrets.ps1` untuk Windows atau `.sh` untuk Linux)
3. File dokumentasi setup (`SETUP_CI_CD.md`) dengan instruksi lengkap
4. Update semua path, port, domain, dan konfigurasi sesuai spesifikasi di atas
```

---

## 📝 CONTOH PENGGUNAAN

### Contoh 1: Repository Baru dengan Port Berbeda

```
Saya ingin mengkonfigurasi CI/CD untuk repository "inventory-system" dengan spesifikasi berikut:

### Informasi Repository:
- **Nama Repository**: inventory-system
- **Branch Utama**: main
- **Path Project di Repository**: src/inventory-app

### Informasi VPS:
- **VPS User**: deploy
- **VPS Host/IP**: 45.76.123.45
- **Deploy Directory di VPS**: /opt/inventory-app

### Informasi Network & Ports:
- **Dashboard Port**: 8080
- **Domain**: inventory.mycompany.com
- **Health Check Endpoint**: /api/health

### Informasi SSH:
- **SSH Key Path** (Windows): C:\Users\admin\.ssh\deploy_key
- **SSH Key Path** (Linux/Mac): ~/.ssh/deploy_key

### Informasi Database:
- **Database Name**: inventory_db
- **Database User**: postgres
- **Database Password**: SecurePass123! (akan di-set sebagai GitHub Secret)

### Konfigurasi Tambahan:
- **Docker Compose File Location**: src/inventory-app/docker-compose.yml
- **Service Names di Docker Compose**: 
  - Dashboard: web
  - Worker: background-worker
  - Database: postgres_db
- **Backup Location**: ~/.inventory-backups

### Fitur yang Diinginkan:
- [x] CI Pipeline (testing, linting, build)
- [x] CD Pipeline (deploy otomatis)
- [x] Security Scanning
- [x] Database Backup sebelum deploy
- [x] Health Check setelah deploy
- [ ] Rollback mechanism

Tolong buatkan file-file yang diperlukan.
```

### Contoh 2: Repository dengan Struktur Berbeda

```
Saya ingin mengkonfigurasi CI/CD untuk repository "analytics-dashboard" dengan spesifikasi berikut:

### Informasi Repository:
- **Nama Repository**: analytics-dashboard
- **Branch Utama**: master
- **Path Project di Repository**: analytics/v2-production

### Informasi VPS:
- **VPS User**: analytics
- **VPS Host/IP**: analytics.company.com
- **Deploy Directory di VPS**: /home/analytics/app

### Informasi Network & Ports:
- **Dashboard Port**: 3000
- **Domain**: dashboard.company.com
- **Health Check Endpoint**: /health

### Informasi SSH:
- **SSH Key Path** (Windows): C:\Users\user\.ssh\analytics_vps
- **SSH Key Path** (Linux/Mac): ~/.ssh/analytics_vps

### Informasi Database:
- **Database Name**: analytics_db
- **Database User**: analytics_user
- **Database Password**: [WILL_BE_SET_AS_SECRET]

### Konfigurasi Tambahan:
- **Docker Compose File Location**: analytics/v2-production
- **Service Names di Docker Compose**: 
  - Dashboard: frontend
  - API: backend
  - Database: mysql_db
- **Backup Location**: /home/analytics/backups

### Fitur yang Diinginkan:
- [x] CI Pipeline
- [x] CD Pipeline
- [x] Security Scanning
- [x] Database Backup
- [x] Health Check

Tolong buatkan file-file yang diperlukan.
```

---

## 🔧 PARAMETER YANG PERLU DIGANTI

Ketika menggunakan prompt ini, pastikan untuk mengganti semua placeholder berikut di file yang dihasilkan:

### Di Workflow Files (`.github/workflows/*.yml`):

| Placeholder | Keterangan | Contoh |
|------------|------------|--------|
| `VPS_USER` | Username SSH di VPS | `deploy`, `admin` |
| `VPS_HOST` | IP atau domain VPS | `192.168.1.100`, `vps.example.com` |
| `VPS_DEPLOY_DIR` | Directory deployment di VPS | `/opt/my-app`, `/home/user/app` |
| `PROJECT_DIR` | Path project di repository | `apps/my-app`, `src/app/V1` |
| Port `5000` | Port dashboard | `8080`, `3000`, `8000` |
| `pzem-monitoring` | Nama project | `my-app`, `inventory-system` |
| Health check URL | Endpoint health check | `/health`, `/api/health` |

### Di Setup Scripts:

| Placeholder | Keterangan | Contoh |
|------------|------------|--------|
| SSH key path | Lokasi SSH private key | `C:\Users\user\.ssh\my_key` |
| `foom@103.31.39.189` | SSH user@host | `deploy@192.168.1.100` |

### Di Docker Compose:

| Placeholder | Keterangan | Contoh |
|------------|------------|--------|
| Port mapping `5000:5000` | Port host:container | `8080:8080`, `3000:3000` |
| Service names | Nama service di docker-compose | `dashboard`, `app`, `web` |
| Database name | Nama database | `pzem_monitoring` → `my_app_db` |

---

## ✅ CHECKLIST SETUP

Setelah file-file dibuat, pastikan untuk:

- [ ] Update GitHub Secrets dengan SSH key yang benar
- [ ] Test SSH connection dari lokal ke VPS
- [ ] Verify VPS memiliki Docker dan Docker Compose terinstall
- [ ] Pastikan directory deployment di VPS memiliki permission yang benar
- [ ] Test workflow secara manual dari GitHub Actions
- [ ] Verify health check endpoint berfungsi
- [ ] Update domain DNS (jika menggunakan custom domain)
- [ ] Configure firewall untuk port yang digunakan
- [ ] Test deployment end-to-end
- [ ] Dokumentasikan konfigurasi khusus untuk tim

---

## 🆘 TROUBLESHOOTING TIPS

### Jika SSH Connection Gagal:
- Pastikan SSH key sudah di-copy ke VPS `~/.ssh/authorized_keys`
- Verify format SSH key di GitHub Secret (harus include BEGIN dan END lines)
- Test SSH connection manual: `ssh -i [key_path] [user]@[host]`

### Jika Port Tidak Bisa Diakses:
- Check firewall di VPS: `sudo ufw status`
- Verify port mapping di docker-compose.yml
- Check apakah service sudah running: `docker ps`

### Jika Deployment Directory Tidak Ada:
- Create directory: `sudo mkdir -p [deploy_dir]`
- Set ownership: `sudo chown -R [user]:[user] [deploy_dir]`
- Verify permission: `ls -la [deploy_dir]`

---

## 📚 CATATAN TAMBAHAN

1. **GitHub Secrets yang Diperlukan:**
   - `VPS_SSH_KEY`: Private SSH key untuk akses VPS
   - `VPS_HOST`: IP atau domain VPS (optional, bisa di-set di workflow)
   - `DB_PASSWORD`: Database password (jika berbeda dari default)

2. **Path Pattern di Workflows:**
   - Jika project ada di subfolder: update `paths` trigger di workflow
   - Contoh: `paths: ['src/my-app/**', '.github/workflows/**']`

3. **Environment Variables:**
   - Jika ada environment variables khusus, tambahkan di `.env` file
   - Pastikan `.env` di-exclude dari git (tambahkan ke `.gitignore`)

4. **Backup Strategy:**
   - Backup location harus writable oleh user deployment
   - Consider backup retention policy (berapa hari backup disimpan)

---

## 🔗 REFERENSI

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [SSH Key Setup Guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)

---

**Template ini dapat digunakan kembali untuk proyek-proyek baru dengan menyesuaikan parameter sesuai kebutuhan.**
# PZEM IoT Monitoring Project

Sistem monitoring energi 3-phase berbasis IoT menggunakan sensor PZEM dengan ESP32, dilengkapi dashboard real-time, laporan PDF, dan CI/CD otomatis.

---

## 🚨 TROUBLESHOOTING - Status PENDING / System Down

**Jika sistem monitoring Anda menunjukkan:**
- ❌ Status "PENDING" (tidak merespons)
- ❌ Response time "N/A"
- ❌ Uptime rendah (<99%)
- ❌ Grafik monitoring banyak bar merah/orange

### 📖 Panduan Lengkap (Bahasa Indonesia):
👉 **[PANDUAN_TROUBLESHOOTING_BAHASA_INDONESIA.md](PANDUAN_TROUBLESHOOTING_BAHASA_INDONESIA.md)** ⭐ **Mulai di sini!**

### ⚡ Quick Fix (5 menit):
👉 **[QUICK_FIX_PENDING.md](QUICK_FIX_PENDING.md)**

### 🔧 Tools & Scripts:

| Tool | Platform | Lokasi | Fungsi |
|------|----------|--------|--------|
| Diagnosis Script | Windows | `.github/diagnose-vps.ps1` | Cek semua masalah otomatis |
| Diagnosis Script | Linux/Mac | `.github/diagnose-vps.sh` | Cek semua masalah otomatis |
| Quick Fix Script | VPS | `.github/quick-fix.sh` | Fix masalah umum |

### 📚 Dokumentasi Troubleshooting:
- **[TROUBLESHOOTING_SUMMARY.md](.github/TROUBLESHOOTING_SUMMARY.md)** - Summary lengkap
- **[TROUBLESHOOTING_README.md](.github/TROUBLESHOOTING_README.md)** - Tools overview
- **[TROUBLESHOOTING_PENDING_STATUS.md](.github/TROUBLESHOOTING_PENDING_STATUS.md)** - Detail step-by-step

---

## 📋 Overview

Project ini terdiri dari dua komponen utama:

1. **ESP32 Firmware** (`ESP32-Multi-Pzem-Main/`) - Firmware untuk ESP32 yang membaca data dari sensor PZEM dan mengirimkannya via MQTT
2. **Monitoring Dashboard** (`pzem-monitoring/V9-Docker/`) - Sistem monitoring berbasis web dengan dashboard real-time, database PostgreSQL, dan generator laporan PDF

## 🏗️ Architecture

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   PZEM      │────────▶│    ESP32     │────────▶│   MQTT       │
│  Sensors    │  Serial │  (Firmware)  │  WiFi   │   Broker     │
└─────────────┘         └──────────────┘         └──────────────┘
                                                         │
                                                         ▼
                                                ┌──────────────┐
                                                │   MQTT       │
                                                │   Client      │
                                                │  (Python)     │
                                                └──────────────┘
                                                         │
                                                         ▼
                                                ┌──────────────┐
                                                │  PostgreSQL  │
                                                │   Database    │
                                                └──────────────┘
                                                         │
                                                         ▼
                                                ┌──────────────┐
                                                │   Flask      │
                                                │  Dashboard   │
                                                │  (Web UI)    │
                                                └──────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker dan Docker Compose
- MQTT Broker (Mosquitto atau cloud MQTT)
- ESP32 dengan sensor PZEM
- Python 3.11+ (untuk development)

### Installation

#### 1. Clone Repository

```bash
git clone <repository-url>
cd PZEM-Project
```

#### 2. Setup ESP32 Firmware

```bash
cd ESP32-Multi-Pzem-Main

# Install PlatformIO jika belum ada
# Buka dengan PlatformIO IDE atau VS Code dengan PlatformIO extension

# Edit config di src/main.cpp untuk MQTT broker settings
# Upload ke ESP32
```

#### 3. Setup Monitoring Dashboard

```bash
cd pzem-monitoring/V9-Docker

# Start services dengan Docker Compose
docker-compose up -d

# Access dashboard
# http://localhost:5000
```

## 📁 Project Structure

```
PZEM-Project/
├── ESP32-Multi-Pzem-Main/      # ESP32 firmware (PlatformIO)
│   ├── src/
│   │   └── main.cpp            # Main firmware code
│   ├── platformio.ini          # PlatformIO configuration
│   └── README.md               # ESP32 documentation
│
├── pzem-monitoring/            # Monitoring system
│   └── V9-Docker/              # Latest Docker version
│       ├── dashboard/          # Flask web application
│       │   ├── app_with_reporting.py
│       │   ├── report_generator.py
│       │   └── requirements.txt
│       ├── mqtt/               # MQTT client
│       │   ├── mqtt_client.py
│       │   └── requirements.txt
│       ├── docker-compose.yml  # Docker configuration
│       └── README.md           # Detailed documentation
│
└── .github/
    └── workflows/               # CI/CD workflows
        ├── ci.yml              # Continuous Integration
        └── deploy.yml          # Continuous Deployment
```

## 🔧 Configuration

### ESP32 Configuration

Edit `ESP32-Multi-Pzem-Main/src/main.cpp`:

```cpp
// WiFi Settings
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// MQTT Settings
const char* mqtt_server = "YOUR_MQTT_BROKER_IP";
const int mqtt_port = 1883;
```

### Dashboard Configuration

Edit `pzem-monitoring/V9-Docker/docker-compose.yml`:

```yaml
environment:
  - DB_HOST=db
  - DB_NAME=pzem_monitoring
  - DB_USER=postgres
  - DB_PASS=Admin123
  - MQTT_BROKER=YOUR_MQTT_BROKER_IP
  - MQTT_PORT=1883
```

## 📊 Features

### Real-time Monitoring
- ✅ 3-phase power consumption tracking
- ✅ Live voltage, current, and power measurements
- ✅ Power factor monitoring
- ✅ Phase imbalance detection
- ✅ WebSocket-based live updates

### Reporting
- ✅ PDF report generation (Daily, Weekly, Monthly)
- ✅ 3-phase system analysis
- ✅ Power trend charts
- ✅ Cost analysis dengan PLN tariff calculation

### CI/CD
- ✅ Automated testing dengan GitHub Actions
- ✅ Automatic deployment ke VPS
- ✅ Security scanning
- ✅ Docker image building

## 🚢 Deployment

### Local Development

```bash
cd pzem-monitoring/V9-Docker
docker-compose up
```

### Production Deployment (VPS)

Project ini sudah dilengkapi dengan CI/CD untuk deployment otomatis ke VPS.

**Setup CI/CD:**

1. Setup GitHub Secrets (lihat [.github/SETUP_CI_CD.md](.github/SETUP_CI_CD.md))
2. Push ke branch `main` atau `master`
3. Deployment akan berjalan otomatis

**Manual Deployment:**

```bash
cd pzem-monitoring/V9-Docker
./deploy-to-vps.sh
```

## 📚 Documentation

- [ESP32 Firmware README](ESP32-Multi-Pzem-Main/README.md)
- [Monitoring Dashboard README](pzem-monitoring/V9-Docker/README.md)
- [CI/CD Setup Guide](.github/SETUP_CI_CD.md)
- [Workflows Documentation](.github/workflows/README.md)

## 🛠️ Development

### Running Tests

```bash
# CI tests akan berjalan otomatis saat push/PR
# Atau jalankan manual:

cd pzem-monitoring/V9-Docker
python -m pytest tests/
```

### Code Style

```bash
# Linting
flake8 dashboard/ mqtt/

# Formatting (jika menggunakan black)
black dashboard/ mqtt/
```

## 🔐 Security

- SSH keys disimpan sebagai GitHub Secrets
- Environment variables untuk sensitive data
- Security scanning dengan Trivy
- Database credentials di environment variables

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📞 Support

Untuk bantuan dan pertanyaan:
- Check documentation di masing-masing folder
- Review logs untuk troubleshooting
- Open issue di GitHub repository

## 🎯 Roadmap

- [ ] Mobile app untuk monitoring
- [ ] Alert/notification system
- [ ] Multi-user support dengan authentication
- [ ] Data export ke Excel/CSV
- [ ] Grafana integration
- [ ] InfluxDB support untuk time-series data

## 🙏 Acknowledgments

- PZEM sensor library
- ESP32 community
- Flask dan Python ecosystem
- Docker community

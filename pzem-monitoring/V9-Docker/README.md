# PZEM 3-Phase Energy Monitoring System

A comprehensive IoT solution for monitoring 3-phase electrical systems using PZEM sensors with real-time data collection, visualization, and PDF reporting capabilities.

## Features

### 🔋 Real-time Monitoring
- 3-phase power consumption tracking
- Live voltage, current, and power measurements
- Power factor and energy consumption monitoring
- System efficiency calculations
- Phase imbalance detection

### 📊 Interactive Dashboard
- Real-time data visualization with charts
- WebSocket-based live updates
- Device status monitoring
- System overview with summary statistics

### 📄 PDF Report Generation
- Comprehensive energy consumption reports
- 3-phase system analysis
- Power trend charts and distribution graphs
- System recommendations and optimization tips
- Cost analysis and energy efficiency metrics

### 🏗️ Architecture
- **MQTT Client**: Collects data from PZEM sensors
- **PostgreSQL Database**: Stores time-series energy data
- **Flask Dashboard**: Web-based monitoring interface
- **Report Generator**: PDF report creation system
- **Docker Containerization**: Easy deployment and scaling

## Quick Start

### Prerequisites
- Docker and Docker Compose
- PZEM sensors with MQTT capability

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd V9-Docker
```

2. Start the services:
```bash
docker-compose up -d
```

3. Access the dashboard:
- Main Dashboard: http://localhost:5000
- Report Generator: http://localhost:5000/reports

### Configuration

Environment variables can be configured in `docker-compose.yml`:

```yaml
environment:
  - DB_HOST=db
  - DB_NAME=pzem_monitoring
  - DB_USER=postgres
  - DB_PASS=Admin123
```

## System Components

### MQTT Client (`mqtt/`)
- Connects to MQTT broker to receive sensor data
- Validates and stores data in PostgreSQL
- Handles device metadata and status tracking
- Automatic reconnection and error recovery

### Dashboard (`dashboard/`)
- Flask web application with SocketIO
- Real-time data visualization
- 3-phase system calculations
- Report generation interface

### Database Schema
- `pzem_data`: Time-series energy measurements
- `pzem_devices`: Device metadata and status

## Report Features

### Report Types
- **Daily Reports**: Last 24 hours analysis
- **Weekly Reports**: 7-day trend analysis  
- **Monthly Reports**: 30-day comprehensive analysis
- **Custom Range**: User-defined date range

### Included Metrics
- Total active, apparent, and reactive power
- Overall power factor and system efficiency
- Phase imbalance analysis (power, current, voltage)
- Energy consumption and cost estimation
- Individual phase performance metrics
- System optimization recommendations

### Charts and Visualizations
- Power consumption trend lines
- Phase distribution pie charts
- High-resolution graphics for professional reports

## API Endpoints

### Dashboard APIs
- `/api/system-status` - Overall system status
- `/api/devices` - Device list and metadata
- `/api/latest/<device>` - Latest device data
- `/api/chart/<device>` - Chart data for device

### Report APIs
- `/reports/generate` - Generate new report
- `/reports/download/<filename>` - Download report
- `/reports/list` - List available reports
- `/reports/api/summary` - Report summary statistics

## Development

### File Structure
```
V9-Docker/
├── dashboard/                 # Flask web application
│   ├── app_with_reporting.py # Main dashboard app
│   ├── report_generator.py   # PDF generation logic
│   ├── report_routes.py      # Report web interface
│   ├── templates/            # HTML templates
│   └── requirements.txt      # Python dependencies
├── mqtt/                     # MQTT data collection
│   ├── mqtt_client.py        # MQTT client implementation
│   └── requirements.txt      # Python dependencies
├── docker-compose.yml        # Container orchestration
└── README.md                # This file
```

### Key Technologies
- **Backend**: Python, Flask, SocketIO
- **Database**: PostgreSQL with time-series optimization
- **Messaging**: MQTT for IoT communication
- **Reports**: ReportLab, Matplotlib for PDF generation
- **Frontend**: HTML5, JavaScript, Chart.js
- **Containerization**: Docker, Docker Compose

## Monitoring and Logging

- Application logs stored in `dashboard.log` and `mqtt_client.log`
- Database connection monitoring with automatic reconnection
- MQTT connection status tracking
- Error handling with detailed logging

## CI/CD with GitHub Actions

This project includes automated CI/CD pipelines for testing and deployment.

### Features
- ✅ **Automated Testing**: Code linting, unit tests, and build verification
- ✅ **Automatic Deployment**: Deploy to VPS on push to main/master
- ✅ **Manual Deployment**: Deploy with options via GitHub Actions UI
- ✅ **Security Scanning**: Automated vulnerability scanning with Trivy

### Quick Setup

1. **Setup SSH Key for VPS:**
   ```bash
   ./setup-github-actions.sh
   ```

2. **Configure GitHub Secrets:**
   - Go to Repository → Settings → Secrets and variables → Actions
   - Add secrets: `VPS_USER`, `VPS_HOST`, `VPS_SSH_KEY`

3. **Automatic Deployment:**
   - Push to `main` or `master` branch → Automatic deployment
   - Check status in **Actions** tab

### Documentation
- 📚 [CI/CD Setup Guide](.github/SETUP_CI_CD.md) - Complete setup instructions
- 📚 [Workflows Documentation](.github/workflows/README.md) - Workflow details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly (CI will run automatically)
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and support:
1. Check the logs for error details
2. Verify MQTT broker connectivity
3. Ensure database is accessible
4. Review configuration settings

## Changelog

### Latest Version (Enhanced)
- ✅ Fixed report generator functionality
- ✅ Improved error handling and logging
- ✅ Enhanced code organization and structure
- ✅ Added comprehensive documentation
- ✅ Optimized Docker configuration
- ✅ Better Windows compatibility
- ✅ Added chart generation with cleanup
- ✅ Improved database connection handling
- ✅ **NEW**: CI/CD with GitHub Actions
- ✅ **NEW**: Automated deployment to VPS
- ✅ **NEW**: PLN billing calculation integration

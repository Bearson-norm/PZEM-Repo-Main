#!/usr/bin/env python3
"""
Windows Setup Script untuk PZEM Monitoring System
"""

import os
import sys
import subprocess
from pathlib import Path

def create_directories():
    """Create necessary directories"""
    directories = ['templates', 'logs', 'backups', 'static']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Directory '{directory}' ready")

def create_dashboard_template():
    """Create dashboard HTML template if it doesn't exist"""
    template_path = Path('templates/dashboard.html')
    
    if template_path.exists():
        print("✅ Dashboard template already exists")
        return
    
    print("📝 Creating dashboard template...")
    
    # Since we have the template in artifacts, we need to create it manually
    dashboard_html = '''<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PZEM Monitoring Dashboard</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    
    <!-- Chart.js -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.3.0/chart.min.js"></script>
    
    <!-- Socket.IO -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
    
    <style>
        .card { border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); }
        .metric-card { background: linear-gradient(45deg, #667eea 0%, #764ba2 100%); color: white; }
        .device-card { background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%); color: white; }
        .status-online { color: #28a745; }
        .status-offline { color: #dc3545; }
        .chart-container { position: relative; height: 400px; }
        .nav-tabs .nav-link.active { background: linear-gradient(45deg, #667eea 0%, #764ba2 100%); color: white; border: none; }
        .navbar { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); }
        .refresh-indicator { position: fixed; top: 20px; right: 20px; z-index: 1000; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="#"><i class="fas fa-bolt"></i> PZEM Monitoring Dashboard</a>
            <div class="navbar-nav ms-auto">
                <span class="navbar-text">
                    <i class="fas fa-wifi status-online"></i>
                    <span id="connectionStatus">Connected</span>
                </span>
            </div>
        </div>
    </nav>

    <div id="refreshIndicator" class="refresh-indicator alert alert-success" style="display: none;">
        <i class="fas fa-sync-alt fa-spin"></i> Data updated!
    </div>

    <div class="container-fluid mt-4">
        <!-- Summary Cards -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <i class="fas fa-microchip fa-3x mb-3"></i>
                        <h5>Total Devices</h5>
                        <h2 id="totalDevices">0</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <i class="fas fa-check-circle fa-3x mb-3"></i>
                        <h5>Online Devices</h5>
                        <h2 id="onlineDevices">0</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <i class="fas fa-bolt fa-3x mb-3"></i>
                        <h5>Total Power</h5>
                        <h2 id="totalPower">0 W</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <i class="fas fa-battery-half fa-3x mb-3"></i>
                        <h5>Total Energy</h5>
                        <h2 id="totalEnergy">0 kWh</h2>
                    </div>
                </div>
            </div>
        </div>

        <!-- Device Cards -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-list"></i> Device Status</h5>
                    </div>
                    <div class="card-body">
                        <div id="deviceCards" class="row"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Charts and Tables -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <ul class="nav nav-tabs card-header-tabs" id="dataTab" role="tablist">
                            <li class="nav-item" role="presentation">
                                <button class="nav-link active" id="chart-tab" data-bs-toggle="tab" data-bs-target="#chart" type="button" role="tab">
                                    <i class="fas fa-chart-line"></i> Charts
                                </button>
                            </li>
                            <li class="nav-item" role="presentation">
                                <button class="nav-link" id="table-tab" data-bs-toggle="tab" data-bs-target="#table" type="button" role="tab">
                                    <i class="fas fa-table"></i> Data Table
                                </button>
                            </li>
                        </ul>
                    </div>
                    <div class="card-body">
                        <div class="tab-content">
                            <div class="tab-pane fade show active" id="chart" role="tabpanel">
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <select class="form-select" id="deviceSelect">
                                            <option value="">Select Device</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="btn-group" role="group">
                                            <input type="radio" class="btn-check" name="period" id="hour" value="hour" checked>
                                            <label class="btn btn-outline-primary" for="hour">Hour</label>
                                            
                                            <input type="radio" class="btn-check" name="period" id="day" value="day">
                                            <label class="btn btn-outline-primary" for="day">Day</label>
                                            
                                            <input type="radio" class="btn-check" name="period" id="week" value="week">
                                            <label class="btn btn-outline-primary" for="week">Week</label>
                                            
                                            <input type="radio" class="btn-check" name="period" id="month" value="month">
                                            <label class="btn btn-outline-primary" for="month">Month</label>
                                        </div>
                                    </div>
                                </div>
                                <div class="chart-container">
                                    <canvas id="powerChart"></canvas>
                                </div>
                            </div>
                            <div class="tab-pane fade" id="table" role="tabpanel">
                                <div class="table-responsive">
                                    <table class="table table-striped table-hover" id="dataTable">
                                        <thead class="table-dark">
                                            <tr>
                                                <th>Device</th>
                                                <th>Timestamp</th>
                                                <th>Voltage (V)</th>
                                                <th>Current (A)</th>
                                                <th>Power (W)</th>
                                                <th>Energy (kWh)</th>
                                                <th>Power Factor</th>
                                                <th>RSSI</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody id="dataTableBody"></tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
    <script>
        const socket = io();
        let chart = null;
        let latestData = {};

        socket.on('connect', function() {
            document.getElementById('connectionStatus').textContent = 'Connected';
            document.getElementById('connectionStatus').previousElementSibling.className = 'fas fa-wifi status-online';
        });

        socket.on('disconnect', function() {
            document.getElementById('connectionStatus').textContent = 'Disconnected';
            document.getElementById('connectionStatus').previousElementSibling.className = 'fas fa-wifi status-offline';
        });

        socket.on('data_update', function(data) {
            latestData = data;
            updateDashboard();
            showRefreshIndicator();
        });

        function showRefreshIndicator() {
            const indicator = document.getElementById('refreshIndicator');
            indicator.style.display = 'block';
            setTimeout(() => indicator.style.display = 'none', 2000);
        }

        async function loadDevices() {
            try {
                const response = await fetch('/api/devices');
                const devices = await response.json();
                
                const select = document.getElementById('deviceSelect');
                select.innerHTML = '<option value="">Select Device</option>';
                devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device[0];
                    option.textContent = `Device ${device[0]}`;
                    select.appendChild(option);
                });

                const latestResponse = await fetch('/api/all-latest');
                latestData = await latestResponse.json();
                updateDashboard();
                
            } catch (error) {
                console.error('Error loading devices:', error);
            }
        }

        function updateDashboard() {
            updateSummaryCards();
            updateDeviceCards();
            updateDataTable();
        }

        function updateSummaryCards() {
            const devices = Object.keys(latestData);
            const onlineDevices = devices.filter(device => {
                const data = latestData[device];
                const lastSeen = new Date(data.created_at);
                return (new Date() - lastSeen) < 10 * 60 * 1000;
            });

            let totalPower = 0, totalEnergy = 0;
            devices.forEach(device => {
                const data = latestData[device];
                totalPower += data.avg_power || 0;
                totalEnergy += data.total_energy || 0;
            });

            document.getElementById('totalDevices').textContent = devices.length;
            document.getElementById('onlineDevices').textContent = onlineDevices.length;
            document.getElementById('totalPower').textContent = totalPower.toFixed(1) + ' W';
            document.getElementById('totalEnergy').textContent = totalEnergy.toFixed(2) + ' kWh';
        }

        function updateDeviceCards() {
            const container = document.getElementById('deviceCards');
            container.innerHTML = '';

            Object.keys(latestData).forEach(deviceAddress => {
                const data = latestData[deviceAddress];
                const lastSeen = new Date(data.created_at);
                const isOnline = (new Date() - lastSeen) < 10 * 60 * 1000;

                const card = document.createElement('div');
                card.className = 'col-md-4 col-lg-3 mb-3';
                card.innerHTML = `
                    <div class="card device-card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 class="card-title">Device ${deviceAddress}</h6>
                                <i class="fas fa-circle ${isOnline ? 'status-online' : 'status-offline'}"></i>
                            </div>
                            <div class="row text-center">
                                <div class="col-6">
                                    <small>Voltage</small>
                                    <div><strong>${(data.avg_voltage || 0).toFixed(1)}V</strong></div>
                                </div>
                                <div class="col-6">
                                    <small>Current</small>
                                    <div><strong>${(data.avg_current || 0).toFixed(2)}A</strong></div>
                                </div>
                            </div>
                            <div class="row text-center mt-2">
                                <div class="col-6">
                                    <small>Power</small>
                                    <div><strong>${(data.avg_power || 0).toFixed(1)}W</strong></div>
                                </div>
                                <div class="col-6">
                                    <small>Energy</small>
                                    <div><strong>${(data.total_energy || 0).toFixed(2)}kWh</strong></div>
                                </div>
                            </div>
                            <div class="mt-2">
                                <small>Power Factor: ${(data.current_power_factor || 0).toFixed(2)}</small><br>
                                <small>RSSI: ${data.wifi_rssi || 0} dBm</small><br>
                                <small>Last: ${lastSeen.toLocaleString()}</small>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        function updateDataTable() {
            const tbody = document.getElementById('dataTableBody');
            tbody.innerHTML = '';

            Object.keys(latestData).forEach(deviceAddress => {
                const data = latestData[deviceAddress];
                const lastSeen = new Date(data.created_at);
                const isOnline = (new Date() - lastSeen) < 10 * 60 * 1000;

                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>Device ${deviceAddress}</td>
                    <td>${lastSeen.toLocaleString()}</td>
                    <td>${(data.avg_voltage || 0).toFixed(1)}</td>
                    <td>${(data.avg_current || 0).toFixed(2)}</td>
                    <td>${(data.avg_power || 0).toFixed(1)}</td>
                    <td>${(data.total_energy || 0).toFixed(2)}</td>
                    <td>${(data.current_power_factor || 0).toFixed(2)}</td>
                    <td>${data.wifi_rssi || 0}</td>
                    <td><span class="badge ${isOnline ? 'bg-success' : 'bg-danger'}">${isOnline ? 'Online' : 'Offline'}</span></td>
                `;
                tbody.appendChild(row);
            });
        }

        function initChart() {
            const ctx = document.getElementById('powerChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: { labels: [], datasets: [
                    { label: 'Voltage (V)', data: [], borderColor: 'rgb(255, 99, 132)', tension: 0.1 },
                    { label: 'Current (A)', data: [], borderColor: 'rgb(54, 162, 235)', tension: 0.1 },
                    { label: 'Power (W)', data: [], borderColor: 'rgb(255, 205, 86)', tension: 0.1 }
                ]},
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        async function updateChart() {
            const deviceAddress = document.getElementById('deviceSelect').value;
            const period = document.querySelector('input[name="period"]:checked').value;

            if (!deviceAddress) {
                chart.data.labels = [];
                chart.data.datasets.forEach(dataset => dataset.data = []);
                chart.update();
                return;
            }

            try {
                const response = await fetch(`/api/chart/${deviceAddress}?period=${period}`);
                const data = await response.json();
                const labels = data.map(item => new Date(item.time_period).toLocaleTimeString());

                chart.data.labels = labels;
                chart.data.datasets[0].data = data.map(item => item.voltage || 0);
                chart.data.datasets[1].data = data.map(item => item.current || 0);
                chart.data.datasets[2].data = data.map(item => item.power || 0);
                chart.update();
            } catch (error) {
                console.error('Error updating chart:', error);
            }
        }

        document.getElementById('deviceSelect').addEventListener('change', updateChart);
        document.querySelectorAll('input[name="period"]').forEach(radio => {
            radio.addEventListener('change', updateChart);
        });

        setInterval(async () => {
            try {
                const response = await fetch('/api/all-latest');
                latestData = await response.json();
                updateDashboard();
                if (document.getElementById('deviceSelect').value) updateChart();
            } catch (error) {
                console.error('Error in auto refresh:', error);
            }
        }, 30000);

        document.addEventListener('DOMContentLoaded', function() {
            loadDevices();
            initChart();
        });
    </script>
</body>
</html>'''
    
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(dashboard_html)
    
    print("✅ Dashboard template created")

def check_requirements():
    """Check Python package requirements"""
    required_packages = [
        'flask==2.3.3',
        'flask-socketio==5.3.6', 
        'psycopg2-binary==2.9.7',
        'paho-mqtt==1.6.1',
        'python-socketio==5.8.0',
        'python-engineio==4.7.1',
        'eventlet==0.33.3'
    ]
    
    print("\n🔍 Checking Python packages...")
    
    missing_packages = []
    for package in required_packages:
        package_name = package.split('==')[0]
        try:
            __import__(package_name.replace('-', '_'))
            print(f"✅ {package_name} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package_name} is missing")
    
    if missing_packages:
        print(f"\n📦 Installing missing packages...")
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing_packages)
        print("✅ Packages installed")
    else:
        print("✅ All packages are installed")

def main():
    print("🪟 PZEM Monitoring - Windows Setup")
    print("="*40)
    
    # Create directories
    create_directories()
    
    # Create dashboard template
    create_dashboard_template()
    
    # Check requirements
    check_requirements()
    
    # Test database connection
    print("\n🗃️ Testing database connection...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            database='pzem_monitoring',
            user='postgres',
            password='Admin123',
            port='5432'
        )
        conn.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please ensure PostgreSQL is running and database exists")
    
    print("\n🎯 Setup completed!")
    print("\nNext steps:")
    print("1. python test_mqtt_data.py  # Test MQTT data sending")
    print("2. python run_system.py      # Start the monitoring system")
    print("3. Open http://localhost:5000 in browser")
    
    input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
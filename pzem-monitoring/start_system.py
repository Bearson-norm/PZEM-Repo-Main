#!/usr/bin/env python3
"""
Script untuk menjalankan sistem PZEM Monitoring secara otomatis
Menjalankan MQTT client dan Flask dashboard bersamaan
"""

import subprocess
import sys
import time
import signal
import os
import threading
from datetime import datetime

class SystemManager:
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def log(self, message, level="INFO"):
        """Log dengan timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def signal_handler(self, signum, frame):
        """Handler untuk graceful shutdown"""
        self.log("Shutting down system...")
        self.running = False
        
        # Terminate all processes
        for name, process in self.processes.items():
            if process and process.poll() is None:
                self.log(f"Terminating {name} (PID: {process.pid})")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.log(f"Force killing {name}", "WARNING")
                    process.kill()
        
        sys.exit(0)
    
    def check_requirements(self):
        """Check if required files and packages exist"""
        self.log("Checking system requirements...")
        
        # Check files
        required_files = ['mqtt_client.py', 'app.py']
        missing_files = []
        
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            self.log(f"Missing files: {', '.join(missing_files)}", "ERROR")
            return False
            
        # Check templates directory
        if not os.path.exists('templates'):
            self.log("Creating templates directory...")
            os.makedirs('templates')
            
        if not os.path.exists('templates/dashboard.html'):
            self.log("templates/dashboard.html not found!", "WARNING")
            self.log("Please save the dashboard HTML file as templates/dashboard.html")
            
        # Check Python packages
        try:
            import flask
            import flask_socketio
            import psycopg2
            import paho.mqtt.client as mqtt
            self.log("All required packages installed")
        except ImportError as e:
            self.log(f"Missing package: {e}", "ERROR")
            self.log("Install with: pip install flask flask-socketio psycopg2-binary paho-mqtt")
            return False
            
        return True
    
    def test_database(self):
        """Test database connection"""
        try:
            import psycopg2
            
            DB_CONFIG = {
                'host': 'localhost',
                'database': 'pzem_monitoring',
                'user': 'postgres',
                'password': 'Admin123'
            }
            
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            
            self.log("Database connection successful")
            return True
            
        except Exception as e:
            self.log(f"Database connection failed: {e}", "ERROR")
            return False
    
    def start_mqtt_client(self):
        """Start MQTT client"""
        self.log("Starting MQTT client...")
        
        try:
            process = subprocess.Popen([
                sys.executable, 'mqtt_client.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
               universal_newlines=True, bufsize=1)
            
            self.processes['mqtt'] = process
            self.log(f"MQTT client started (PID: {process.pid})")
            return process
            
        except Exception as e:
            self.log(f"Failed to start MQTT client: {e}", "ERROR")
            return None
    
    def start_flask_app(self):
        """Start Flask dashboard"""
        self.log("Starting Flask dashboard...")
        
        try:
            # Set environment variables
            env = os.environ.copy()
            env['FLASK_ENV'] = 'production'
            env['FLASK_DEBUG'] = '0'
            
            process = subprocess.Popen([
                sys.executable, 'app.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
               universal_newlines=True, bufsize=1, env=env)
            
            self.processes['flask'] = process
            self.log(f"Flask app started (PID: {process.pid})")
            return process
            
        except Exception as e:
            self.log(f"Failed to start Flask app: {e}", "ERROR")
            return None
    
    def monitor_process(self, name, process):
        """Monitor a process and restart if needed"""
        while self.running:
            if process.poll() is not None:
                # Process died
                self.log(f"{name} process terminated unexpectedly", "WARNING")
                
                if self.running:  # Only restart if system is still running
                    self.log(f"Restarting {name}...")
                    
                    if name == 'mqtt':
                        new_process = self.start_mqtt_client()
                    elif name == 'flask':
                        new_process = self.start_flask_app()
                    else:
                        break
                        
                    if new_process:
                        self.processes[name] = new_process
                        process = new_process
                    else:
                        self.log(f"Failed to restart {name}", "ERROR")
                        break
            
            time.sleep(5)  # Check every 5 seconds
    
    def show_logs(self, name, process):
        """Show process logs"""
        while self.running and process.poll() is None:
            # Read stdout
            if process.stdout and process.stdout.readable():
                line = process.stdout.readline()
                if line:
                    self.log(f"[{name}] {line.strip()}")
            
            # Read stderr
            if process.stderr and process.stderr.readable():
                line = process.stderr.readline()
                if line:
                    self.log(f"[{name}] ERROR: {line.strip()}")
            
            time.sleep(0.1)
    
    def run(self):
        """Run the complete system"""
        print("=" * 60)
        print("PZEM Monitoring System - Auto Start")
        print("=" * 60)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Check requirements
        if not self.check_requirements():
            self.log("System requirements not met", "ERROR")
            return
        
        # Test database
        if not self.test_database():
            self.log("Database test failed", "WARNING")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                return
        
        # Start MQTT client
        mqtt_process = self.start_mqtt_client()
        if not mqtt_process:
            self.log("Cannot start MQTT client", "ERROR")
            return
        
        # Wait for MQTT to initialize
        time.sleep(3)
        
        # Start Flask app  
        flask_process = self.start_flask_app()
        if not flask_process:
            self.log("Cannot start Flask app", "ERROR")
            return
        
        # Wait for Flask to start
        time.sleep(3)
        
        self.log("System started successfully!")
        self.log("Dashboard URL: http://localhost:5000")
        self.log("Press Ctrl+C to shutdown")
        print("-" * 60)
        
        # Start monitoring threads
        mqtt_monitor = threading.Thread(
            target=self.monitor_process, 
            args=('mqtt', mqtt_process),
            daemon=True
        )
        flask_monitor = threading.Thread(
            target=self.monitor_process, 
            args=('flask', flask_process),
            daemon=True
        )
        
        mqtt_log = threading.Thread(
            target=self.show_logs,
            args=('MQTT', mqtt_process),
            daemon=True
        )
        flask_log = threading.Thread(
            target=self.show_logs,
            args=('FLASK', flask_process),
            daemon=True
        )
        
        mqtt_monitor.start()
        flask_monitor.start()
        mqtt_log.start()
        flask_log.start()
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
                
                # Check if all processes are still alive
                active_processes = sum(1 for p in self.processes.values() 
                                     if p and p.poll() is None)
                
                if active_processes == 0 and self.running:
                    self.log("All processes terminated", "ERROR")
                    break
                    
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("PZEM Monitoring System Auto Start")
            print("Usage: python start_system.py [options]")
            print("\nOptions:")
            print("  --help     Show this help")
            print("  --debug    Run debug checks first")
            return
        
        elif sys.argv[1] == '--debug':
            print("Running debug checks...")
            import subprocess
            subprocess.run([sys.executable, 'debug_system.py'])
            return
    
    manager = SystemManager()
    manager.run()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Script untuk menjalankan seluruh sistem PZEM Monitoring
"""

import subprocess
import sys
import time
import signal
import os
from threading import Thread

class SystemManager:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def signal_handler(self, signum, frame):
        """Handler untuk graceful shutdown"""
        print("\n[INFO] Shutting down system...")
        self.running = False
        
        # Terminate all processes
        for process in self.processes:
            if process.poll() is None:  # Process still running
                print(f"[INFO] Terminating process {process.pid}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"[WARNING] Force killing process {process.pid}")
                    process.kill()
        
        sys.exit(0)
    
    def check_requirements(self):
        """Check if required packages are installed"""
        try:
            import flask
            import flask_socketio
            import psycopg2
            import paho.mqtt.client as mqtt
            print("[INFO] All required packages are installed")
            return True
        except ImportError as e:
            print(f"[ERROR] Missing required package: {e}")
            print("[INFO] Please install requirements: pip install -r requirements.txt")
            return False
    
    def check_database_connection(self):
        """Check database connection"""
        try:
            import psycopg2
            
            # Database config (sesuaikan dengan konfigurasi Anda)
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
            
            print("[INFO] Database connection successful")
            return True
            
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            print("[INFO] Please check your PostgreSQL installation and database setup")
            return False
    
    def start_mqtt_client(self):
        """Start MQTT client in subprocess"""
        print("[INFO] Starting MQTT client...")
        
        if not os.path.exists('mqtt_client.py'):
            print("[ERROR] mqtt_client.py not found!")
            return None
            
        process = subprocess.Popen([
            sys.executable, 'mqtt_client.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
           universal_newlines=True)
        
        return process
    
    def start_flask_app(self):
        """Start Flask dashboard in subprocess"""
        print("[INFO] Starting Flask dashboard...")
        
        if not os.path.exists('app.py'):
            print("[ERROR] app.py not found!")
            return None
        
        # Set environment variables
        env = os.environ.copy()
        env['FLASK_ENV'] = 'production'
        env['FLASK_DEBUG'] = '0'
        
        process = subprocess.Popen([
            sys.executable, 'app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
           universal_newlines=True, env=env)
        
        return process
    
    def monitor_process(self, process, name):
        """Monitor a process and log its output"""
        while self.running and process.poll() is None:
            line = process.stdout.readline()
            if line:
                print(f"[{name}] {line.strip()}")
        
        if process.poll() is not None and self.running:
            print(f"[WARNING] {name} process terminated unexpectedly")
    
    def run(self):
        """Run the complete system"""
        print("="*50)
        print("PZEM Monitoring System")
        print("="*50)
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Check requirements
        if not self.check_requirements():
            return
        
        # Check database
        if not self.check_database_connection():
            print("[INFO] You can continue without database, but data won't be saved")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                return
        
        # Create templates directory if it doesn't exist
        if not os.path.exists('templates'):
            os.makedirs('templates')
            print("[INFO] Created templates directory")
        
        # Check if dashboard.html exists in templates
        if not os.path.exists('templates/dashboard.html'):
            print("[WARNING] templates/dashboard.html not found!")
            print("[INFO] Please save the HTML template as templates/dashboard.html")
        
        # Start MQTT client
        mqtt_process = self.start_mqtt_client()
        if mqtt_process:
            self.processes.append(mqtt_process)
            # Start monitoring thread for MQTT
            mqtt_thread = Thread(target=self.monitor_process, 
                                args=(mqtt_process, "MQTT"))
            mqtt_thread.daemon = True
            mqtt_thread.start()
        
        # Wait a bit for MQTT to initialize
        time.sleep(2)
        
        # Start Flask app
        flask_process = self.start_flask_app()
        if flask_process:
            self.processes.append(flask_process)
            # Start monitoring thread for Flask
            flask_thread = Thread(target=self.monitor_process, 
                                 args=(flask_process, "FLASK"))
            flask_thread.daemon = True
            flask_thread.start()
        
        print("\n[INFO] System started successfully!")
        print("[INFO] Dashboard available at: http://localhost:5000")
        print("[INFO] Press Ctrl+C to shutdown")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
                
                # Check if processes are still running
                for i, process in enumerate(self.processes[:]):
                    if process.poll() is not None:
                        print(f"[WARNING] Process {i} terminated")
                        self.processes.remove(process)
                
                # If all processes died, exit
                if not self.processes and self.running:
                    print("[ERROR] All processes terminated")
                    break
                    
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)

def main():
    # Check if running as script or module
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("PZEM Monitoring System Runner")
            print("Usage: python run_system.py [options]")
            print("Options:")
            print("  --help     Show this help message")
            print("  --check    Check system requirements only")
            return
        
        if sys.argv[1] == '--check':
            manager = SystemManager()
            print("Checking system requirements...")
            if manager.check_requirements() and manager.check_database_connection():
                print("[INFO] System is ready to run!")
            else:
                print("[ERROR] System is not ready")
            return
    
    # Run the system
    manager = SystemManager()
    manager.run()

if __name__ == "__main__":
    main()
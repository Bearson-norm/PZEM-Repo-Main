#!/usr/bin/env python3
"""
Simple System Runner untuk PZEM Monitoring (No SocketIO)
"""

import subprocess
import sys
import time
import signal
import os
from threading import Thread
import psycopg2

class SimpleSystemManager:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def signal_handler(self, signum, frame):
        """Handler untuk graceful shutdown"""
        print("\n[INFO] Shutting down system...")
        self.running = False
        
        # Terminate all processes
        for process in self.processes:
            if process.poll() is None:
                print(f"[INFO] Terminating process {process.pid}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"[WARNING] Force killing process {process.pid}")
                    process.kill()
        
        sys.exit(0)
    
    def check_basic_requirements(self):
        """Check basic requirements (no flask-socketio)"""
        try:
            import flask
            import psycopg2
            import paho.mqtt.client as mqtt
            print("[INFO] Basic packages are available")
            return True
        except ImportError as e:
            print(f"[ERROR] Missing required package: {e}")
            print("[INFO] Please install: pip install flask psycopg2-binary paho-mqtt")
            return False
    
    def check_database_connection(self):
        """Check database connection"""
        try:
            conn = psycopg2.connect(
                host='localhost',
                database='pzem_monitoring', 
                user='postgres',
                password='Admin123'
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            
            print("[INFO] Database connection successful")
            return True
            
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return False
    
    def create_template_if_missing(self):
        """Create simple dashboard template if missing"""
        template_path = 'templates/simple_dashboard.html'
        
        if not os.path.exists('templates'):
            os.makedirs('templates')
            print("[INFO] Created templates directory")
        
        if not os.path.exists(template_path):
            print("[INFO] Creating simple dashboard template...")
            # The template will be created by simple_flask_app.py automatically
            return True
        
        print("[INFO] Template already exists")
        return True
    
    def start_mqtt_client(self):
        """Start MQTT client"""
        print("[INFO] Starting MQTT client...")
        
        if not os.path.exists('mqtt_client.py'):
            print("[ERROR] mqtt_client.py not found!")
            return None
            
        process = subprocess.Popen([
            sys.executable, 'mqtt_client.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
           universal_newlines=True)
        
        return process
    
    def start_simple_flask_app(self):
        """Start simple Flask app"""
        print("[INFO] Starting Simple Flask dashboard...")
        
        if not os.path.exists('simple_flask_app.py'):
            print("[ERROR] simple_flask_app.py not found!")
            return None
        
        process = subprocess.Popen([
            sys.executable, 'simple_flask_app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
           universal_newlines=True)
        
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
        print("PZEM Monitoring System (Simple Version)")
        print("="*50)
        
        # Setup signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Check basic requirements
        if not self.check_basic_requirements():
            return
        
        # Check database
        if not self.check_database_connection():
            print("[INFO] Please ensure PostgreSQL is running and database exists")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                return
        
        # Create template if missing
        self.create_template_if_missing()
        
        # Start MQTT client
        mqtt_process = self.start_mqtt_client()
        if mqtt_process:
            self.processes.append(mqtt_process)
            mqtt_thread = Thread(target=self.monitor_process, 
                                args=(mqtt_process, "MQTT"))
            mqtt_thread.daemon = True
            mqtt_thread.start()
        
        # Wait for MQTT to initialize
        time.sleep(3)
        
        # Start Flask app
        flask_process = self.start_simple_flask_app()
        if flask_process:
            self.processes.append(flask_process)
            flask_thread = Thread(target=self.monitor_process, 
                                 args=(flask_process, "FLASK"))
            flask_thread.daemon = True
            flask_thread.start()
        
        print("\n[INFO] System started successfully!")
        print("[INFO] Dashboard available at: http://localhost:5000")
        print("[INFO] Features:")
        print("      - Auto-refresh every 30 seconds")
        print("      - Device monitoring") 
        print("      - Charts and data tables")
        print("      - No WebSocket (polling-based)")
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
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("Simple PZEM Monitoring System Runner")
            print("Usage: python simple_run_system.py [options]")
            print("Options:")
            print("  --help     Show this help message")
            print("  --check    Check system requirements only")
            return
        
        if sys.argv[1] == '--check':
            manager = SimpleSystemManager()
            print("Checking system requirements...")
            if manager.check_basic_requirements() and manager.check_database_connection():
                print("[INFO] System is ready to run!")
            else:
                print("[ERROR] System is not ready")
            return
    
    # Run the system
    manager = SimpleSystemManager()
    manager.run()

if __name__ == "__main__":
    main()
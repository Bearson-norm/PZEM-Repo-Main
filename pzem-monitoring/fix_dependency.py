#!/usr/bin/env python3
"""
Script untuk memperbaiki konflik Flask-SocketIO
"""

import subprocess
import sys
import os

def uninstall_conflicting_packages():
    """Uninstall packages yang konflik"""
    packages_to_remove = [
        'flask-socketio',
        'python-socketio',
        'python-engineio',
        'eventlet'
    ]
    
    print("🔧 Removing conflicting packages...")
    for package in packages_to_remove:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'uninstall', package, '-y'], 
                         capture_output=True, text=True)
            print(f"✅ Removed {package}")
        except Exception as e:
            print(f"⚠️ Could not remove {package}: {e}")

def install_compatible_versions():
    """Install versi yang kompatibel"""
    compatible_packages = [
        'python-engineio==4.7.1',
        'python-socketio==5.8.0', 
        'flask-socketio==5.3.4',
        'eventlet==0.33.3'
    ]
    
    print("\n📦 Installing compatible versions...")
    for package in compatible_packages:
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Installed {package}")
            else:
                print(f"❌ Failed to install {package}")
                print(result.stderr)
        except Exception as e:
            print(f"❌ Error installing {package}: {e}")

def test_imports():
    """Test import packages"""
    print("\n🧪 Testing imports...")
    
    try:
        import flask
        print("✅ Flask imported successfully")
    except ImportError as e:
        print(f"❌ Flask import failed: {e}")
    
    try:
        import flask_socketio
        print("✅ Flask-SocketIO imported successfully")
    except ImportError as e:
        print(f"❌ Flask-SocketIO import failed: {e}")
        return False
    
    try:
        import psycopg2
        print("✅ psycopg2 imported successfully")
    except ImportError as e:
        print(f"❌ psycopg2 import failed: {e}")
    
    try:
        import paho.mqtt.client as mqtt
        print("✅ paho-mqtt imported successfully")
    except ImportError as e:
        print(f"❌ paho-mqtt import failed: {e}")
    
    return True

def main():
    print("🔧 Flask-SocketIO Compatibility Fix")
    print("="*40)
    
    # Step 1: Uninstall conflicting packages
    uninstall_conflicting_packages()
    
    # Step 2: Install compatible versions
    install_compatible_versions()
    
    # Step 3: Test imports
    if test_imports():
        print("\n✅ All packages installed successfully!")
        print("\nYou can now run:")
        print("python run_system.py")
    else:
        print("\n❌ Some packages failed to install")
        print("\nTry manual installation:")
        print("pip install flask==2.3.3")
        print("pip install flask-socketio==5.3.4")
        print("pip install python-socketio==5.8.0")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test script untuk mengecek API endpoints dashboard
"""

import requests
import json
import time

BASE_URL = 'http://localhost:5000/api'

def test_endpoint(endpoint, description):
    """Test single API endpoint"""
    print(f"\n=== Testing {endpoint} - {description} ===")
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response type: {type(data)}")
            
            if isinstance(data, dict):
                print(f"Keys: {list(data.keys())}")
                if len(data) > 0:
                    first_key = list(data.keys())[0]
                    print(f"Sample data ({first_key}): {data[first_key]}")
            elif isinstance(data, list):
                print(f"Array length: {len(data)}")
                if len(data) > 0:
                    print(f"Sample item: {data[0]}")
            else:
                print(f"Data: {data}")
                
            # Test JSON serialization
            json_str = json.dumps(data)
            print(f"JSON serialization: OK ({len(json_str)} chars)")
            
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to dashboard (is it running?)")
    except Exception as e:
        print(f"ERROR: {e}")

def test_all_endpoints():
    """Test semua API endpoints"""
    print("PZEM Dashboard API Test")
    print("=" * 50)
    
    # Test basic endpoints
    endpoints = [
        ("/system-status", "System overview"),
        ("/devices", "Device list"),
        ("/all-latest", "Latest data from all devices"),
    ]
    
    for endpoint, description in endpoints:
        test_endpoint(endpoint, description)
    
    # Test device-specific endpoints (if we have devices)
    print(f"\n=== Getting device list for specific tests ===")
    try:
        response = requests.get(f"{BASE_URL}/devices", timeout=10)
        if response.status_code == 200:
            devices_data = response.json()
            
            if isinstance(devices_data, list) and len(devices_data) > 0:
                # Get first device address
                first_device = devices_data[0]
                if isinstance(first_device, dict):
                    device_address = first_device.get('device_address')
                elif isinstance(first_device, list):
                    device_address = first_device[0]
                else:
                    device_address = None
                
                if device_address:
                    print(f"Testing with device: {device_address}")
                    
                    device_endpoints = [
                        (f"/latest/{device_address}", f"Latest data for device {device_address}"),
                        (f"/data/{device_address}?period=hour", f"Hour data for device {device_address}"),
                        (f"/chart/{device_address}?period=hour", f"Chart data for device {device_address}"),
                    ]
                    
                    for endpoint, description in device_endpoints:
                        test_endpoint(endpoint, description)
                else:
                    print("Could not determine device address format")
            else:
                print("No devices found for device-specific tests")
    except:
        print("Could not get devices for specific tests")

def test_websocket_simulation():
    """Simulate what frontend JavaScript would receive"""
    print(f"\n=== Frontend JavaScript Simulation ===")
    
    try:
        # Test /api/devices (untuk dropdown)
        devices_response = requests.get(f"{BASE_URL}/devices")
        if devices_response.status_code == 200:
            devices = devices_response.json()
            print(f"\nDevice Select Options:")
            print("- All Devices")
            
            if isinstance(devices, list):
                for device in devices:
                    if isinstance(device, dict):
                        addr = device.get('device_address', 'unknown')
                        count = device.get('data_count', 0)
                        name = device.get('device_name', f'Device {addr}')
                        print(f"- {name} ({count} records)")
                    elif isinstance(device, list) and len(device) >= 2:
                        print(f"- Device {device[0]} ({device[1]} records)")
        
        # Test /api/all-latest (untuk device list dan table)
        latest_response = requests.get(f"{BASE_URL}/all-latest")
        if latest_response.status_code == 200:
            latest_data = latest_response.json()
            print(f"\nDevice List Cards:")
            
            for device_addr, data in latest_data.items():
                power = data.get('power', 0) or 0
                voltage = data.get('voltage', 0) or 0
                current = data.get('current', 0) or 0
                energy = data.get('energy', 0) or 0
                
                print(f"- Device {device_addr}:")
                print(f"  Power: {power} W")
                print(f"  Voltage: {voltage} V") 
                print(f"  Current: {current} A")
                print(f"  Energy: {energy} kWh")
                
                # Check for problematic values
                if power is None or power == 0:
                    print(f"  ⚠️  Power is {power}")
                if voltage is None or voltage == 0:
                    print(f"  ⚠️  Voltage is {voltage}")
        
    except Exception as e:
        print(f"Frontend simulation error: {e}")

def main():
    print("Starting API endpoint tests...")
    print("Make sure the dashboard is running on localhost:5000")
    time.sleep(1)
    
    test_all_endpoints()
    test_websocket_simulation()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("\nIf you see issues:")
    print("1. Check if dashboard is running: python app_windows.py")
    print("2. Check database has data: python debug_dashboard.py") 
    print("3. Check browser console for JavaScript errors")

if __name__ == "__main__":
    main()
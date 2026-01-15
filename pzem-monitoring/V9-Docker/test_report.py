#!/usr/bin/env python3
"""
Quick test script to verify report generation works without hanging
"""

import requests
import time
import json

def test_report_generation():
    """Test the report generation endpoint"""
    base_url = "http://localhost:5000"
    
    print("🔋 Testing PZEM Report Generator")
    print("================================")
    
    # Test 1: Check if dashboard is accessible
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Dashboard is accessible")
            health_data = response.json()
            print(f"   Status: {health_data.get('status', 'unknown')}")
        else:
            print(f"❌ Dashboard health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to dashboard: {e}")
        return False
    
    # Test 2: Check report page
    try:
        response = requests.get(f"{base_url}/reports", timeout=10)
        if response.status_code == 200:
            print("✅ Report page is accessible")
        else:
            print(f"❌ Report page failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Report page error: {e}")
    
    # Test 3: Try to generate a daily report
    print("\n📊 Testing report generation...")
    try:
        start_time = time.time()
        response = requests.get(
            f"{base_url}/reports/generate",
            params={'period_type': 'daily'},
            timeout=60  # 60 second timeout
        )
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"   Generation took: {duration:.2f} seconds")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Report generated successfully!")
                print(f"   Filename: {result.get('filename')}")
                return True
            else:
                print(f"❌ Report generation failed: {result.get('error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False
            
    except requests.Timeout:
        print("❌ Report generation timed out (>60 seconds)")
        return False
    except Exception as e:
        print(f"❌ Report generation error: {e}")
        return False

if __name__ == "__main__":
    success = test_report_generation()
    if success:
        print("\n🎉 All tests passed! Report generator is working correctly.")
    else:
        print("\n❌ Tests failed. Check the logs for more details.")
        print("   Run: docker-compose logs dashboard --tail=50")

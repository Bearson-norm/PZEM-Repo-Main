#!/usr/bin/env python3
"""
Script untuk test koneksi database PostgreSQL
Membantu troubleshooting masalah koneksi
"""

import psycopg2
import sys
import os

def test_connection(config, description):
    """Test database connection with given config"""
    print(f"\n🔍 Testing: {description}")
    print(f"   Config: {config}")
    
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        print(f"   ✅ SUCCESS: Connected to PostgreSQL")
        print(f"   📊 Version: {version}")
        return True
        
    except psycopg2.Error as e:
        print(f"   ❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def main():
    print("🔧 PostgreSQL Connection Test")
    print("==============================")
    
    # Test configurations in order of preference
    test_configs = [
        # Standard connection with password
        {
            'config': {
                'host': 'localhost',
                'database': 'pzem_monitoring',
                'user': 'postgres', 
                'password': 'Admin123',
                'port': '5432'
            },
            'description': 'Standard connection (password: postgres)'
        },
        
        # Trust authentication (no password)
        {
            'config': {
                'host': 'localhost',
                'database': 'pzem_monitoring',
                'user': 'postgres',
                'port': '5432'
            },
            'description': 'Trust authentication (no password)'
        },
        
        # Peer authentication (local socket)
        {
            'config': {
                'database': 'pzem_monitoring',
                'user': 'postgres'
            },
            'description': 'Peer authentication (local socket)'
        },
        
        # Alternative password
        {
            'config': {
                'host': 'localhost',
                'database': 'pzem_monitoring',
                'user': 'postgres', 
                'password': '',
                'port': '5432'
            },
            'description': 'Empty password'
        },
        
        # Alternative user
        {
            'config': {
                'host': 'localhost',
                'database': 'pzem_monitoring',
                'user': os.getenv('USER', 'postgres'),
                'port': '5432'
            },
            'description': f'Current system user ({os.getenv("USER", "unknown")})'
        }
    ]
    
    successful_configs = []
    
    for test in test_configs:
        if test_connection(test['config'], test['description']):
            successful_configs.append(test)
    
    print(f"\n📋 RESULTS")
    print("=" * 30)
    
    if successful_configs:
        print(f"✅ Found {len(successful_configs)} working configuration(s):")
        
        for i, config in enumerate(successful_configs, 1):
            print(f"\n{i}. {config['description']}")
            print("   Update config.py with:")
            
            cfg = config['config']
            if 'host' in cfg:
                print(f"   DB_HOST = '{cfg['host']}'")
            if 'port' in cfg:
                print(f"   DB_PORT = '{cfg['port']}'")
            print(f"   DB_USER = '{cfg['user']}'")
            if 'password' in cfg:
                print(f"   DB_PASSWORD = '{cfg['password']}'")
            print(f"   DB_NAME = '{cfg['database']}'")
        
        print(f"\n💡 Recommended: Use configuration #1 for your application")
        
    else:
        print("❌ No working configurations found!")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check if PostgreSQL is running:")
        print("   sudo systemctl status postgresql")
        print("2. Check if database exists:")
        print("   sudo -u postgres psql -l | grep pzem_monitoring")
        print("3. Create database if missing:")
        print("   sudo -u postgres createdb pzem_monitoring")
        print("4. Check authentication method in pg_hba.conf")
        print("5. Reset postgres password:")
        print("   sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'postgres';\"")
    
    # Test table existence if we have a working connection
    if successful_configs:
        print(f"\n🗃️  Testing table structure...")
        config = successful_configs[0]['config']
        
        try:
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            
            # Check if pzem_data table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'pzem_data'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if table_exists:
                print("   ✅ Table 'pzem_data' exists")
                
                # Check table structure
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'pzem_data'
                    ORDER BY ordinal_position;
                """)
                
                columns = cursor.fetchall()
                print(f"   📊 Found {len(columns)} columns in pzem_data table")
                
                # Check for problematic column names
                problem_columns = []
                for col_name, col_type in columns:
                    if col_name in ['timestamp', 'current_time']:
                        problem_columns.append(col_name)
                
                if problem_columns:
                    print(f"   ⚠️  Found problematic column names: {problem_columns}")
                    print("   💡 Run fix_database.sql to resolve schema issues")
                else:
                    print("   ✅ Table schema looks good")
                    
            else:
                print("   ❌ Table 'pzem_data' does not exist")
                print("   💡 Run database_setup.sql to create tables")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"   ❌ Error checking tables: {e}")

if __name__ == "__main__":
    main()
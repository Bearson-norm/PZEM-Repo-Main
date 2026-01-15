#!/usr/bin/env python3
"""
File konfigurasi untuk PZEM Monitoring System
Sesuaikan konfigurasi sesuai dengan environment Anda
"""

import os

class Config:
    """Konfigurasi dasar"""
    
    # MQTT Configuration
    MQTT_BROKER = "103.87.67.139"
    MQTT_PORT = 1883
    MQTT_KEEPALIVE = 60
    MQTT_TOPIC = "sensor/pzem/+"  # Subscribe ke semua device
    MQTT_QOS = 1
    
    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'pzem_monitoring')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'Admin123')  # Updated with correct password
    DB_PORT = os.getenv('DB_PORT', '5432')
    
    # Flask Configuration
    FLASK_HOST = '0.0.0.0'
    FLASK_PORT = 5000
    FLASK_DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key_change_this')
    
    # System Configuration
    LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
    LOG_FILE = 'pzem_monitoring.log'
    DATA_RETENTION_DAYS = 90  # Berapa hari data disimpan
    
    # Monitoring Configuration
    DEVICE_OFFLINE_THRESHOLD = 600  # Device dianggap offline setelah 10 menit
    AUTO_REFRESH_INTERVAL = 30  # Refresh dashboard setiap 30 detik
    
    # Chart Configuration
    MAX_CHART_POINTS = 100  # Maksimal titik data di chart
    
    @classmethod
    def get_db_config(cls):
        """Return database configuration dictionary"""
        return {
            'host': cls.DB_HOST,
            'database': cls.DB_NAME,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
            'port': cls.DB_PORT
        }
    
    @classmethod
    def get_mqtt_config(cls):
        """Return MQTT configuration dictionary"""
        return {
            'broker': cls.MQTT_BROKER,
            'port': cls.MQTT_PORT,
            'keepalive': cls.MQTT_KEEPALIVE,
            'topic': cls.MQTT_TOPIC,
            'qos': cls.MQTT_QOS
        }

class DevelopmentConfig(Config):
    """Konfigurasi untuk development"""
    FLASK_DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Konfigurasi untuk production"""
    FLASK_DEBUG = False
    LOG_LEVEL = 'INFO'
    
    # Production security settings
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required in production")

class TestingConfig(Config):
    """Konfigurasi untuk testing"""
    TESTING = True
    DB_NAME = 'pzem_test'

# Pilih konfigurasi berdasarkan environment
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on FLASK_ENV environment variable"""
    env = os.getenv('FLASK_ENV', 'default')
    return config_map.get(env, DevelopmentConfig)
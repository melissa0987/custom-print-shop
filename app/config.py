# app/config.py

import os, secrets
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration"""
    
    # Database Configuration
    DATABASE_HOST = os.environ.get('DATABASE_HOST')
    DATABASE_PORT = int(os.environ.get('DATABASE_PORT'))
    DATABASE_NAME = os.environ.get('DATABASE_NAME')
    DATABASE_USER = os.environ.get('DATABASE_USER')
    DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD')
    DATABASE_SSLMODE = os.environ.get('DATABASE_SSLMODE', 'disable')
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    
    # Session Configuration
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # File Upload
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Application Settings
    DEBUG = False
    TESTING = False
    
    # Database Pool Settings
    DB_POOL_MIN = 2
    DB_POOL_MAX = 20
    
    # CORS Settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else []
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
    }

    # """Return a list of missing or invalid configuration keys"""
    def validate_config(self):
        errors = []

        required_keys = [
            'DATABASE_HOST',
            'DATABASE_PORT',
            'DATABASE_NAME',
            'DATABASE_USER',
            'DATABASE_PASSWORD',
            'SECRET_KEY'
        ]

        for key in required_keys:
            if getattr(self, key, None) in [None, '']:
                errors.append(f"Missing configuration: {key}")

        return errors


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    # Add stricter security headers for production
    SECURITY_HEADERS = {
        **Config.SECURITY_HEADERS,
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'",
    }


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    DATABASE_NAME = 'test_custom_print'


def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'production')
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
    }
    
    return config_map.get(env, ProductionConfig)()
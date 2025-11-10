import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

class Config:
    """Secure configuration class that uses environment variables"""
    
    # Database Configuration (use environment variables with defaults)
    DATABASE_HOST = os.environ.get('DATABASE_HOST')
    DATABASE_NAME = os.environ.get('DATABASE_NAME')
    DATABASE_USER = os.environ.get('DATABASE_USER')
    DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD')
    DATABASE_PORT = int(os.environ.get('DATABASE_PORT'))
    DATABASE_SSLMODE = os.environ.get('DB_SSLMODE', 'disable')
    
    # Security Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    CSRF_SECRET_KEY = os.environ.get('CSRF_SECRET_KEY', secrets.token_hex(32))
    
    # Session Configuration
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', '7200'))  # 2 hours
    SESSION_SECURE = True  # Cookies only sent over HTTPS
    SESSION_HTTPONLY = True  # Cookies not accessible via JavaScript
    SESSION_SAMESITE = 'Lax'  # CSRF protection
    
    # SSL/TLS Configuration
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'True').lower() == 'true'
    SSL_CERT_PATH = os.environ.get('SSL_CERT_PATH', 'cert.pem')
    SSL_KEY_PATH = os.environ.get('SSL_KEY_PATH', 'key.pem')
    
    # Rate Limiting Configuration
    RATE_LIMITING = True
    LOGIN_RATE_LIMIT = os.environ.get('LOGIN_RATE_LIMIT', '10 per minute')
    GENERAL_RATE_LIMIT = os.environ.get('GENERAL_RATE_LIMIT', '100 per hour')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    LOG_SENSITIVE_DATA = False  # Never log sensitive data
    
    # Account Security
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', '5'))
    LOCKOUT_DURATION_MINUTES = int(os.environ.get('LOCKOUT_DURATION_MINUTES', '15'))
    
    # Password Policy
    MIN_PASSWORD_LENGTH = int(os.environ.get('MIN_PASSWORD_LENGTH', '8'))
    REQUIRE_UPPERCASE = os.environ.get('REQUIRE_UPPERCASE', 'True').lower() == 'true'
    REQUIRE_LOWERCASE = os.environ.get('REQUIRE_LOWERCASE', 'True').lower() == 'true'
    REQUIRE_NUMBERS = os.environ.get('REQUIRE_NUMBERS', 'True').lower() == 'true'
    REQUIRE_SPECIAL_CHARS = os.environ.get('REQUIRE_SPECIAL_CHARS', 'True').lower() == 'true'
    
    # File Upload Configuration for Custom Printing
    UPLOAD_FOLDER = os.path.join('static', os.environ.get('UPLOAD_FOLDER', 'uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', '16777216'))  # 16MB for design files
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'ai', 'svg', 'psd'}  # Design file formats
    
    # Static Files Configuration
    STATIC_FOLDER = 'static'
    STATIC_URL_PATH = '/static'
    
    # CORS Configuration (restrictive by default)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else []
    
    # Development vs Production
    DEBUG = os.environ.get('FLASK_ENV', 'production') == 'development'
    TESTING = os.environ.get('TESTING', 'False').lower() == 'true'
    
    # Database URL for connection pooling
    @staticmethod
    def get_database_url():
        """Get database URL without exposing credentials in logs"""
        return f"postgresql://{Config.DATABASE_USER}:{Config.DATABASE_PASSWORD}@{Config.DATABASE_HOST}:{Config.DATABASE_PORT}/{Config.DATABASE_NAME}?sslmode={Config.DATABASE_SSLMODE}"

    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    # Application Limits
    MAX_TRANSACTION_AMOUNT = float(os.environ.get('MAX_TRANSACTION_AMOUNT', '10000.00'))
    DAILY_TRANSACTION_LIMIT = float(os.environ.get('DAILY_TRANSACTION_LIMIT', '50000.00'))
    
    # Backup Configuration
    BACKUP_ENCRYPTION_KEY = os.environ.get('BACKUP_ENCRYPTION_KEY', secrets.token_hex(32))
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
    
    # Audit Configuration
    ENABLE_AUDIT_LOG = os.environ.get('ENABLE_AUDIT_LOG', 'True').lower() == 'true'
    AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', '365'))
    
    @classmethod
    def validate_config(cls):
        """Validate configuration settings"""
        errors = []
        
        # Check required environment variables
        required_vars = ['DATABASE_PASSWORD', 'SECRET_KEY']
        for var in required_vars:
            if not os.environ.get(var):
                errors.append(f"Missing required environment variable: {var}")
        
        # Check password policy
        if cls.MIN_PASSWORD_LENGTH < 8:
            errors.append("MIN_PASSWORD_LENGTH must be at least 8")
        
        # Check session timeout
        if cls.SESSION_TIMEOUT < 300:  # 5 minutes minimum
            errors.append("SESSION_TIMEOUT must be at least 300 seconds (5 minutes)")
        
        # Check transaction limits
        if cls.MAX_TRANSACTION_AMOUNT <= 0:
            errors.append("MAX_TRANSACTION_AMOUNT must be positive")
        
        if cls.DAILY_TRANSACTION_LIMIT <= cls.MAX_TRANSACTION_AMOUNT:
            errors.append("DAILY_TRANSACTION_LIMIT must be greater than MAX_TRANSACTION_AMOUNT")
        
        return errors
    
    @classmethod
    def get_safe_config(cls):
        """Get configuration without sensitive data for debugging"""
        return {
            'DATABASE_HOST': cls.DATABASE_HOST,
            'DATABASE_NAME': cls.DATABASE_NAME,
            'DATABASE_PORT': cls.DATABASE_PORT,
            'DEBUG': cls.DEBUG,
            'SESSION_TIMEOUT': cls.SESSION_TIMEOUT,
            'FORCE_HTTPS': cls.FORCE_HTTPS,
            'RATE_LIMITING': cls.RATE_LIMITING,
            'MAX_LOGIN_ATTEMPTS': cls.MAX_LOGIN_ATTEMPTS,
            'MIN_PASSWORD_LENGTH': cls.MIN_PASSWORD_LENGTH,
            'MAX_TRANSACTION_AMOUNT': cls.MAX_TRANSACTION_AMOUNT
        }

class ProductionConfig(Config):
    """Production-specific configuration"""
    DEBUG = False
    TESTING = False
    FORCE_HTTPS = True
    SESSION_SECURE = True
    
    # Stricter rate limits in production
    LOGIN_RATE_LIMIT = '5 per minute'
    GENERAL_RATE_LIMIT = '50 per hour'

class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    FORCE_HTTPS = False  # Allow HTTP in development
    SESSION_SECURE = False  # Allow non-HTTPS cookies in development
    
    # More lenient rate limits in development
    LOGIN_RATE_LIMIT = '20 per minute'
    GENERAL_RATE_LIMIT = '200 per hour'

class TestingConfig(Config):
    """Testing-specific configuration"""
    TESTING = True
    DEBUG = True
    FORCE_HTTPS = False
    SESSION_SECURE = False
    
    # Use test database for testing
    DATABASE_NAME = 'test_printingdb'
    
    # Disable rate limiting for tests
    RATE_LIMITING = False

# Configuration factory
def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'production')
    
    if env == 'development':
        return DevelopmentConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return ProductionConfig()
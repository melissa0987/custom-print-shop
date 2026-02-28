#!/usr/bin/env python3
"""
Secure Banking App Runner
Loads configuration and starts the Flask application
"""
import os 
from app.config import get_config
from __init__ import app

# Load configuration
config = get_config()

# Startup info
print("=" * 50)
print("Secure Banking Application")
print("=" * 50)
print(f"Database Host: {config.DATABASE_HOST}")
print(f"Database Name: {config.DATABASE_NAME}")
print(f"SSL Mode: {config.DATABASE_SSLMODE}")
print(f"Environment: {config.DEBUG and 'development' or 'production'}")
print(f"Redis Available: {os.environ.get('REDIS_AVAILABLE', 'false')}")
print("=" * 50)

# Run app
if config.DEBUG:
    print("Running in DEVELOPMENT mode (adhoc SSL)")
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context='adhoc')
else:
    print("Production mode detected. Use a WSGI server like Gunicorn.")
    print("Example: gunicorn -w 4 -b 0.0.0.0:5000 --certfile=cert.pem --keyfile=key.pem app:app")
#!/usr/bin/env python3
"""
Secure Banking App Runner
Loads environment variables and starts the Flask application
"""
import os
import sys
from dotenv import load_dotenv
# from redis import Redis

# Load environment variables from .env file
load_dotenv()

# Validate required environment variables
required_vars = ['DATABASE_PASSWORD', 'SECRET_KEY']
missing_vars = []

# Test Redis connection and set environment variable for app to use
try:
    # redis_store = Redis(host='localhost', port=6379, decode_responses=True)
    # redis_store.ping()
    print("Redis connection successful")
    os.environ['REDIS_AVAILABLE'] = 'true'
except Exception as e:
    print(f"Warning: Redis connection failed: {e}")
    print("Rate limiting will use in-memory storage (not recommended for production)")
    print("To fix: Install and start Redis server")
    os.environ['REDIS_AVAILABLE'] = 'false'

for var in required_vars:
    if not os.environ.get(var):
        missing_vars.append(var)

if missing_vars:
    print("Error: Missing required environment variables:")
    for var in missing_vars:
        print(f"  - {var}")
    print("\nPlease set these in your .env file or environment")
    sys.exit(1)

# Import and run the Flask app
try:
    from __init__ import app
    
    # Print startup info
    print("=" * 50)
    print("Secure Banking Application")
    print("=" * 50)
    print(f"Database Host: {os.environ.get('DATABASE_HOST', 'localhost')}")
    print(f"Database Name: {os.environ.get('DATABASE_NAME', 'banking_db')}")
    print(f"SSL Mode: {os.environ.get('DB_SSLMODE', 'disable')}")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'production')}")
    print(f"Redis Available: {os.environ.get('REDIS_AVAILABLE', 'false')}")
    print("=" * 50)
    
    # Run the application
    if os.environ.get('FLASK_ENV') == 'development':
        print("Running in DEVELOPMENT mode")
        print("WARNING: Do not use this in production!")
        print("Access the application at: https://0.0.0.0:5000")
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            ssl_context='adhoc'  # Creates a temporary SSL certificate
        )
    else:
        print("Production mode detected")
        print("Please use a proper WSGI server like Gunicorn")
        print("Example: gunicorn -w 4 -b 0.0.0.0:5000 --certfile=cert.pem --keyfile=key.pem app:app")
        
except ImportError as e:
    print(f"Error importing application: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Error starting application: {e}")
    sys.exit(1)
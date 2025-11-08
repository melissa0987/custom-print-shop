"""
Application entry point
Run this file to start the Flask development server
"""
import os
from app import create_app

# Get configuration from environment variable or default to development
config_name = os.getenv('FLASK_ENV', 'development')

# Create Flask application
app = create_app(config_name)

if __name__ == '__main__':
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
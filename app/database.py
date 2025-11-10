"""
Database connection and session management using Flask-SQLAlchemy with psycopg2
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import psycopg2
from psycopg2 import pool
from flask import current_app
import logging

# Create SQLAlchemy and Migrate instances
db = SQLAlchemy()
migrate = Migrate()

# Connection pool for direct psycopg2 connections (used by model classes)
connection_pool = None

logger = logging.getLogger(__name__)


def init_connection_pool(app):
    """
    Initialize a connection pool for psycopg2 connections.
    This is used by the model classes that use direct psycopg2.
    """
    global connection_pool
    
    try:
        connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            host=app.config['DATABASE_HOST'],
            port=app.config['DATABASE_PORT'],
            database=app.config['DATABASE_NAME'],
            user=app.config['DATABASE_USER'],
            password=app.config['DATABASE_PASSWORD'],
            options=f"-c search_path=public"
        )
        logger.info("Database connection pool initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {e}")
        return False


def get_db_connection():
    """
    Get a connection from the pool.
    Used by model classes for direct psycopg2 operations.
    """
    global connection_pool
    
    if connection_pool is None:
        raise Exception("Connection pool not initialized")
    
    try:
        conn = connection_pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"Failed to get connection from pool: {e}")
        raise


def release_db_connection(conn):
    """
    Return a connection to the pool.
    """
    global connection_pool
    
    if connection_pool is not None and conn is not None:
        connection_pool.putconn(conn)


def close_connection_pool():
    """
    Close all connections in the pool.
    Should be called on application shutdown.
    """
    global connection_pool
    
    if connection_pool is not None:
        connection_pool.closeall()
        logger.info("Database connection pool closed")


def init_db(app):
    """
    Initialize the database and migration engine with the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Bind SQLAlchemy and Migrate to the Flask app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize connection pool for psycopg2
    with app.app_context():
        init_connection_pool(app)
    
    # Register shutdown handler
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Clean up database sessions on application context teardown"""
        db.session.remove()
    
    logger.info(f"Database initialized: {app.config['DATABASE_NAME']} on {app.config['DATABASE_HOST']}")


def test_connection(app):
    """
    Test database connection.
    Returns True if connection is successful, False otherwise.
    """
    try:
        # Test SQLAlchemy connection
        with app.app_context():
            db.engine.connect()
            logger.info("SQLAlchemy database connection test: SUCCESS")
        
        # Test psycopg2 connection pool
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            cursor.close()
            release_db_connection(conn)
            logger.info(f"psycopg2 connection pool test: SUCCESS - {version[0]}")
            return True
        
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def create_tables(app):
    """
    Create all database tables.
    Note: With psycopg2 models, tables should be created using SQL scripts.
    This function is for SQLAlchemy models if you add any.
    """
    with app.app_context():
        db.create_all()
        logger.info("Database tables created (SQLAlchemy models only)")


def drop_tables(app):
    """
    Drop all database tables.
    WARNING: This will delete all data!
    """
    with app.app_context():
        db.drop_all()
        logger.warning("All database tables dropped!")
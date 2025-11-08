"""
Database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager

# Create base class for declarative models
Base = declarative_base()

# Database engine and session (will be initialized by init_db)
engine = None
SessionLocal = None


def init_db(app):
    """
    Initialize database connection with Flask app configuration
    
    Args:
        app: Flask application instance
    """
    global engine, SessionLocal
    
    # Create database engine
    engine = create_engine(
        app.config['SQLALCHEMY_DATABASE_URI'],
        echo=app.config['SQLALCHEMY_ECHO'],
        pool_pre_ping=True,  # Enable connection health checks
        pool_size=10,
        max_overflow=20
    )
    
    # Create session factory
    session_factory = sessionmaker(bind=engine)
    SessionLocal = scoped_session(session_factory)
    
    return engine


def get_db():
    """
    Get database session
    
    Returns:
        Database session
    """
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


@contextmanager
def get_db_session():
    """
    Context manager for database sessions
    
    Usage:
        with get_db_session() as session:
            # Use session here
            pass
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_db_session(exception=None):
    """
    Close database session (for Flask teardown)
    
    Args:
        exception: Exception that occurred (if any)
    """
    if SessionLocal:
        SessionLocal.remove()
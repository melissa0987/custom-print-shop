"""
# app/database.py
Database Module - psycopg2 Connection Management (Simplified)
"""
import psycopg2, os
from psycopg2 import pool, Error as PgError
from psycopg2.extras import RealDictCursor
from flask import g, has_app_context
from contextlib import contextmanager
import logging, time

logger = logging.getLogger(__name__)

# Global connection pool
_connection_pool = None


# ================================================================
# INITIALIZATION
# ================================================================

"""Initialize the PostgreSQL connection pool with Flask config."""
def init_db(app): 
    global _connection_pool

    try:
        if _connection_pool:
            _connection_pool.closeall()

        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=app.config.get("DB_POOL_MIN", 2),
            maxconn=app.config.get("DB_POOL_MAX", 10),
            host=app.config["DATABASE_HOST"],
            port=app.config["DATABASE_PORT"],
            dbname=app.config["DATABASE_NAME"],
            user=app.config["DATABASE_USER"],
            password=app.config["DATABASE_PASSWORD"],
            cursor_factory=RealDictCursor
        )

        logger.info(f"Database pool initialized for {app.config['DATABASE_NAME']}")

    except KeyError as e:
        logger.error(f"Missing DB config: {e}")
        raise
    except PgError as e:
        logger.error(f"Failed to initialize DB pool: {e}")
        raise

"""Close all database connections."""
def close_db(): 
    global _connection_pool
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("Database pool closed.")


# ================================================================
# CONNECTION HELPERS
# ================================================================
"""Get a DB connection from the pool."""
def get_connection(): 
    if not _connection_pool:
        raise ConnectionError("Database pool not initialized.")
    
    conn = _connection_pool.getconn()  

    if has_app_context():   
        g.db_conn = conn

    return conn

"""Return a connection to the pool."""
def release_connection(conn): 
    if conn and _connection_pool:
        _connection_pool.putconn(conn)
        if hasattr(g, "db_conn"):
            delattr(g, "db_conn")

# ================================================================
# EXECUTE SQL FILE
# ================================================================
def execute_sql_file(filepath):
    """Execute SQL commands from a file."""
    if not os.path.exists(filepath):
        logger.error(f"SQL file not found: {filepath}")
        return False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        if not sql_content.strip():
            logger.warning(f"SQL file is empty: {filepath}")
            return False

        with get_cursor() as cur:
            cur.execute(sql_content)

        logger.info(f"Successfully executed SQL file: {filepath}")
        return True

    except Exception as e:
        logger.error(f"Error executing SQL file {filepath}: {e}")
        return False


# ================================================================
# CONTEXT MANAGER FOR QUERIES
# ================================================================
"""Provide a cursor with auto commit/rollback and cleanup."""
@contextmanager
def get_cursor(commit=True): 
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            release_connection(conn)


# ================================================================
# QUERY HELPERS
# ================================================================
"""Run a single SQL query safely."""
def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    with get_cursor() as cur:
        cur.execute(query, params)
        if fetch_one:
            return cur.fetchone()
        elif fetch_all:
            return cur.fetchall()
        return None

"""Run multiple queries (bulk insert/update)."""
def execute_many(query, params_list): 
    with get_cursor() as cur:
        cur.executemany(query, params_list)


# ================================================================
# HEALTH CHECK
# ================================================================
"""Check database connectivity and response time."""
def health_check():
    status = {"status": "unhealthy", "response_time_ms": None}
    if not _connection_pool:
        status["error"] = "Connection pool not initialized"
        return status

    try:
        start = time.time()
        with get_cursor(commit=False) as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()
        elapsed = round((time.time() - start) * 1000, 2)

        status.update({
            "status": "healthy" if result else "unhealthy",
            "response_time_ms": elapsed
        })
    except Exception as e:
        status["error"] = str(e)
    return status

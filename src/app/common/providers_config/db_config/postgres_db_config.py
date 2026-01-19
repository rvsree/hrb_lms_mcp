# src/app/common/providers_config/db_config/postgres_db_config.py
"""
PostgreSQL Database Configuration.

This module provides configuration functions for PostgreSQL database connections.
PostgreSQL is used for Long-Term Memory (LTM) and Entity Memory storage.

Environment Variables:
    POSTGRES_DB_HOST: Database host (default: localhost)
    POSTGRES_DB_PORT: Database port (default: 5432)
    POSTGRES_DB_NAME: Database name (default: coco)
    POSTGRES_DB_USER: Database user (default: postgres)
    POSTGRES_DB_PASSWORD: Database password
    POSTGRES_DB_SSLMODE: SSL mode (default: disable)
    
    Alternative (takes precedence):
    POSTGRES_DSN: Full connection string
    DATABASE_URL: Full connection string (for cloud providers)
"""

import os
from typing import Optional

from dotenv import load_dotenv

from src.app.common.config.app_logging import get_logger

logger = get_logger("postgres_db_config")

load_dotenv()


def get_postgres_host() -> str:
    """
    Read POSTGRES_DB_HOST or POSTGRES_HOST from environment or .env.
    
    Returns:
        Database host (default: localhost)
    """
    return os.getenv("POSTGRES_DB_HOST") or os.getenv("POSTGRES_HOST", "localhost")


def get_postgres_port() -> int:
    """
    Read POSTGRES_DB_PORT or POSTGRES_PORT from environment or .env.
    
    Returns:
        Database port (default: 5432)
    """
    raw = os.getenv("POSTGRES_DB_PORT") or os.getenv("POSTGRES_PORT", "5432")
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid POSTGRES_DB_PORT '%s', using 5432.", raw)
        return 5432


def get_postgres_name() -> str:
    """
    Read POSTGRES_DB_NAME or POSTGRES_DB from environment or .env.
    
    Returns:
        Database name (default: hrb_demo)
    """
    return os.getenv("POSTGRES_DB_NAME") or os.getenv("POSTGRES_DB", "hrb_demo")


def get_postgres_user() -> str:
    """
    Read POSTGRES_DB_USER or POSTGRES_USER from environment or .env.
    
    Returns:
        Database user (default: postgres)
    """
    return os.getenv("POSTGRES_DB_USER") or os.getenv("POSTGRES_USER", "postgres")


def get_postgres_password() -> Optional[str]:
    """
    Read POSTGRES_DB_PASSWORD or POSTGRES_PASSWORD from environment or .env.
    
    Returns:
        Database password or None if not set.
    """
    return os.getenv("POSTGRES_DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")


def get_postgres_sslmode() -> str:
    """
    Read POSTGRES_DB_SSLMODE from environment or .env.
    
    Returns:
        SSL mode (default: disable)
        Options: disable, allow, prefer, require, verify-ca, verify-full
    """
    return os.getenv("POSTGRES_DB_SSLMODE", "disable")


def get_postgres_dsn() -> str:
    """
    Build or retrieve PostgreSQL connection string (DSN).
    
    Precedence:
        1. POSTGRES_DSN environment variable
        2. DATABASE_URL environment variable
        3. Assembled from individual POSTGRES_DB_* variables
        
    Returns:
        PostgreSQL connection string
        
    Raises:
        ValueError: If DSN cannot be constructed (missing required fields)
    """
    # Check for full DSN first
    for env_key in ("POSTGRES_DSN", "DATABASE_URL", "DB_URL"):
        dsn = os.getenv(env_key)
        if dsn:
            logger.debug("Using %s for Postgres connection.", env_key)
            return dsn
    
    # Assemble from parts
    host = get_postgres_host()
    port = get_postgres_port()
    name = get_postgres_name()
    user = get_postgres_user()
    password = get_postgres_password()
    sslmode = get_postgres_sslmode()
    
    if not user or not name:
        raise ValueError(
            "PostgreSQL DSN could not be constructed. "
            "Set POSTGRES_DSN, DATABASE_URL, or provide POSTGRES_DB_USER and POSTGRES_DB_NAME."
        )
    
    if password:
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{name}?sslmode={sslmode}"
    else:
        dsn = f"postgresql://{user}@{host}:{port}/{name}?sslmode={sslmode}"
    
    logger.debug("Constructed Postgres DSN for host=%s, db=%s", host, name)
    return dsn


def get_postgres_pool_size() -> int:
    """
    Read POSTGRES_DB_POOL_SIZE from environment or .env.
    
    Returns:
        Connection pool size (default: 5)
    """
    raw = os.getenv("POSTGRES_DB_POOL_SIZE", "5")
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid POSTGRES_DB_POOL_SIZE '%s', using 5.", raw)
        return 5


def get_postgres_pool_timeout() -> int:
    """
    Read POSTGRES_DB_POOL_TIMEOUT from environment or .env.
    
    Returns:
        Pool connection timeout in seconds (default: 30)
    """
    raw = os.getenv("POSTGRES_DB_POOL_TIMEOUT", "30")
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid POSTGRES_DB_POOL_TIMEOUT '%s', using 30.", raw)
        return 30

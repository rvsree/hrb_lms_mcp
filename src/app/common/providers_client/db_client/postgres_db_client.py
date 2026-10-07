# src/app/common/providers_client/db_client/postgres_db_client.py
"""
PostgreSQL connection management and health check.

Only used by:
- common/auth/token_service.py (get_postgres_connection, for the
  hrb_lms_mcp_auth.oauth_clients lookup)
- api/mcp_server.py (postgres_health_check, for the /hrb_emp_lms/health
  endpoint)

Everything else (leave balance/request/HITL data access) goes through
SQLAlchemy ORM models in repos/database.py instead - this module never
touches that data. Trimmed 2026-10-07: this file used to also carry ~470
lines of Long-Term-Memory/Entity/Conversation-history CRUD functions for
an "agent memory" feature that was never wired into any real code path
(confirmed via a zero-reference grep across src/) and whose own schema
file (postgres_agent_memory_schema.sql) didn't even exist in the repo -
removed rather than kept as aspirational dead code.
"""

from contextlib import contextmanager
from typing import Any, Dict, Iterator

import psycopg
from psycopg.rows import dict_row

from src.app.common.config.app_logging import get_logger
from src.app.common.providers_config.db_config.postgres_db_config import (
    get_postgres_dsn,
    get_postgres_pool_timeout,
)

logger = get_logger("postgres_db_client")


def get_postgres_connection() -> psycopg.Connection:
    """
    Open a psycopg connection using the configured DSN.

    Returns:
        psycopg.Connection instance

    Raises:
        RuntimeError: If connection fails
    """
    try:
        dsn = get_postgres_dsn()
        timeout = get_postgres_pool_timeout()
        conn = psycopg.connect(dsn, connect_timeout=timeout)
        return conn
    except ValueError as ve:
        logger.error("Postgres DSN resolution failed: %s", ve)
        raise RuntimeError(str(ve)) from ve
    except Exception as exc:
        logger.exception("Failed to create Postgres connection")
        raise RuntimeError(
            "Unable to connect to PostgreSQL. Check DSN, network, and credentials."
        ) from exc


@contextmanager
def postgres_session(autocommit: bool = False) -> Iterator[psycopg.Connection]:
    """
    Context manager yielding a psycopg connection.

    Commits on success, rolls back on exception, always closes.

    Args:
        autocommit: If True, each statement auto-commits

    Yields:
        psycopg.Connection instance
    """
    conn = get_postgres_connection()
    try:
        conn.autocommit = autocommit
        yield conn
        if not autocommit:
            conn.commit()
    except Exception:
        if not autocommit:
            try:
                conn.rollback()
            except Exception:
                logger.exception("Rollback failed")
        logger.exception("Transaction failed")
        raise
    finally:
        try:
            conn.close()
        except Exception:
            logger.exception("Failed closing Postgres connection")


def postgres_health_check() -> Dict[str, Any]:
    """
    Health check for PostgreSQL database.

    Returns:
        Dict with status, message, and connection details.
    """
    try:
        with postgres_session() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT 1 AS health_check, version() AS version")
                row = cur.fetchone()

                if not row:
                    return {
                        "status": "unhealthy",
                        "message": "PostgreSQL health check returned no rows.",
                    }

                return {
                    "status": "healthy",
                    "message": "Connected to PostgreSQL successfully.",
                    "version": row.get("version", "unknown")[:50] + "...",
                }

    except Exception as exc:
        logger.exception("Postgres health check failed.")
        return {
            "status": "unhealthy",
            "message": f"PostgreSQL check failed: {exc}",
        }

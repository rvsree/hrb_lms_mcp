# src/app/common/providers_client/db_client/postgres_db_client.py
"""
PostgreSQL Database Client for Agent Memory.

This module provides functions for:
- Database connection management
- Schema initialization for agent memory tables
- Long-Term Memory (LTM) CRUD operations (UNUSED in hrb_emp_lms)
- Entity Memory CRUD operations (UNUSED in hrb_emp_lms)
- Conversation history operations (UNUSED in hrb_emp_lms)

NOTE: LTM/Entity/Conversation functions are marked as UNUSED because:
- hrb_emp_lms MCP server uses SQLAlchemy ORM models (database.py) for data access
- Services (LeaveBalanceService, LeaveRequestService, HitlService) use SQLAlchemy
- Only postgres_health_check() is actively used by the health endpoint

Tables managed:
- agent_ltm: Long-term memory storage (not used by current MCP implementation)
- agent_entities: Named entity memory (not used by current MCP implementation)
- agent_conversations: Conversation history (not used by current MCP implementation)
"""

import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

import psycopg
from psycopg.rows import dict_row

from src.app.common.config.app_logging import get_logger
from src.app.common.providers_config.db_config.postgres_db_config import (
    get_postgres_dsn,
    get_postgres_pool_timeout,
)

logger = get_logger("postgres_db_client")


# ---------------------------------------------------------------------------
# Connection Management
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Schema Initialization
# ---------------------------------------------------------------------------


def _table_exists(cur: psycopg.Cursor, table_name: str) -> bool:
    """Check if a table exists in the database."""
    cur.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        )
        """,
        (table_name,),
    )
    result = cur.fetchone()
    return result[0] if result else False


def init_agent_memory_schema() -> None:
    """
    Ensure agent memory tables exist in PostgreSQL.
    
    Loads DDL from postgres_agent_memory_schema.sql.
    Creates tables: agent_ltm, agent_entities, agent_conversations
    """
    with postgres_session() as conn:
        with conn.cursor() as cur:
            has_ltm = _table_exists(cur, "agent_ltm")
            has_entities = _table_exists(cur, "agent_entities")
            has_conversations = _table_exists(cur, "agent_conversations")
            
            if has_ltm and has_entities and has_conversations:
                logger.debug("PostgreSQL agent memory schema already exists.")
                return
            
            # Load schema from SQL file
            base_dir = os.path.dirname(__file__)
            # Navigate up from db_client to common, then into db_scripts/postgres
            common_dir = os.path.dirname(os.path.dirname(base_dir))
            schema_path = os.path.join(
                common_dir, "db_scripts", "postgres", "postgres_agent_memory_schema.sql"
            )
            schema_path = os.path.abspath(schema_path)
            
            if not os.path.exists(schema_path):
                raise FileNotFoundError(
                    f"postgres_agent_memory_schema.sql not found at {schema_path}. "
                    "Expected at: src/app/common/db_scripts/postgres/"
                )
            
            with open(schema_path, "r", encoding="utf-8") as f:
                ddl = f.read()
            
            cur.execute(ddl)
            conn.commit()
            
            logger.info(
                "Initialized PostgreSQL agent memory schema from %s",
                schema_path,
            )


# ---------------------------------------------------------------------------
# SQL Query Loader
# ---------------------------------------------------------------------------


def _load_postgres_queries() -> Dict[str, str]:
    """
    Load DML statements from postgres_sql_queries.sql into a dict.
    
    Queries are identified by -- NAME: markers.
    """
    base_dir = os.path.dirname(__file__)
    # Navigate up from db_client to common, then into db_scripts/postgres
    common_dir = os.path.dirname(os.path.dirname(base_dir))
    queries_path = os.path.join(
        common_dir, "db_scripts", "postgres", "postgres_sql_queries.sql"
    )
    queries_path = os.path.abspath(queries_path)
    
    queries: Dict[str, str] = {}
    
    if not os.path.exists(queries_path):
        logger.warning("postgres_sql_queries.sql not found at %s", queries_path)
        return queries
    
    current_name: Optional[str] = None
    current_lines: List[str] = []
    
    with open(queries_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            
            if line.startswith("-- NAME:"):
                # Flush previous block
                if current_name and current_lines:
                    queries[current_name] = "\n".join(current_lines).strip()
                current_name = line.split(":", 1)[1].strip()
                current_lines = []
            else:
                if current_name:
                    current_lines.append(raw_line.rstrip("\n"))
    
    if current_name and current_lines:
        queries[current_name] = "\n".join(current_lines).strip()
    
    logger.info("Loaded %d Postgres SQL queries from %s", len(queries), queries_path)
    return queries


_POSTGRES_QUERIES: Dict[str, str] = {}


def _ensure_queries_loaded() -> None:
    """Ensure SQL queries are loaded (lazy loading)."""
    global _POSTGRES_QUERIES
    if not _POSTGRES_QUERIES:
        _POSTGRES_QUERIES = _load_postgres_queries()


def _sql(name: str) -> str:
    """Get SQL query by name from loaded queries."""
    _ensure_queries_loaded()
    sql = _POSTGRES_QUERIES.get(name)
    if not sql:
        raise RuntimeError(
            f"SQL query '{name}' not found in postgres_sql_queries.sql "
            "(check -- NAME: markers and file path)."
        )
    return sql


# ---------------------------------------------------------------------------
# Long-Term Memory (LTM) Operations
# ---------------------------------------------------------------------------
# UNUSED: These functions are not used by hrb_emp_lms MCP server.
# Services use SQLAlchemy ORM (database.py) instead of direct psycopg.
# TODO: Remove if agent memory features are not planned.


def insert_ltm_memory(
    user_id: str,
    memory_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Insert a long-term memory record.
    
    Args:
        user_id: User identifier
        memory_type: Type of memory ('fact', 'preference', 'history')
        content: Memory content
        metadata: Optional JSON metadata
        
    Returns:
        Generated memory ID (UUID)
    """
    memory_id = str(uuid.uuid4())
    
    with postgres_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _sql("INSERT_LTM_MEMORY"),
                {
                    "id": memory_id,
                    "user_id": user_id,
                    "memory_type": memory_type,
                    "content": content,
                    "metadata": psycopg.types.json.Json(metadata) if metadata else None,
                },
            )
    
    logger.info("Inserted LTM memory id=%s for user=%s", memory_id, user_id)
    return memory_id


def query_ltm_memories(
    user_id: str,
    memory_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Query long-term memories for a user.
    
    Args:
        user_id: User identifier
        memory_type: Optional filter by memory type
        limit: Maximum records to return
        offset: Pagination offset
        
    Returns:
        List of memory records
    """
    with postgres_session() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if memory_type:
                cur.execute(
                    _sql("SELECT_LTM_BY_USER_AND_TYPE"),
                    {"user_id": user_id, "memory_type": memory_type, "limit": limit, "offset": offset},
                )
            else:
                cur.execute(
                    _sql("SELECT_LTM_BY_USER"),
                    {"user_id": user_id, "limit": limit, "offset": offset},
                )
            
            rows = cur.fetchall()
    
    return [dict(row) for row in rows]


def delete_ltm_memory(memory_id: str) -> bool:
    """
    Delete a long-term memory by ID.
    
    Args:
        memory_id: Memory UUID
        
    Returns:
        True if deleted, False if not found
    """
    with postgres_session() as conn:
        with conn.cursor() as cur:
            cur.execute(_sql("DELETE_LTM_BY_ID"), {"id": memory_id})
            deleted = cur.rowcount > 0
    
    if deleted:
        logger.info("Deleted LTM memory id=%s", memory_id)
    
    return deleted


# ---------------------------------------------------------------------------
# Entity Memory Operations
# ---------------------------------------------------------------------------
# UNUSED: These functions are not used by hrb_emp_lms MCP server.
# Services use SQLAlchemy ORM (database.py) instead of direct psycopg.
# TODO: Remove if agent memory features are not planned.


def upsert_entity(
    entity_name: str,
    entity_type: str,
    description: Optional[str] = None,
    source_context: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Insert or update an entity in memory.
    
    If entity exists (by name), updates description and increments mention count.
    
    Args:
        entity_name: Name of the entity
        entity_type: Type ('document', 'person', 'concept', 'date', etc.)
        description: Description of the entity
        source_context: Context where entity was mentioned
        metadata: Optional JSON metadata
        
    Returns:
        Entity ID (UUID)
    """
    entity_id = str(uuid.uuid4())
    
    with postgres_session() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Check if entity exists
            cur.execute(
                _sql("SELECT_ENTITY_BY_NAME"),
                {"entity_name": entity_name},
            )
            existing = cur.fetchone()
            
            if existing:
                # Update existing entity
                cur.execute(
                    _sql("UPDATE_ENTITY_MENTION"),
                    {
                        "id": existing["id"],
                        "description": description or existing["description"],
                        "source_context": source_context,
                    },
                )
                entity_id = existing["id"]
                logger.info("Updated entity '%s' (id=%s)", entity_name, entity_id)
            else:
                # Insert new entity
                cur.execute(
                    _sql("INSERT_ENTITY"),
                    {
                        "id": entity_id,
                        "entity_name": entity_name,
                        "entity_type": entity_type,
                        "description": description,
                        "source_context": source_context,
                        "metadata": psycopg.types.json.Json(metadata) if metadata else None,
                    },
                )
                logger.info("Inserted new entity '%s' (id=%s)", entity_name, entity_id)
    
    return entity_id


def query_entities(
    entity_type: Optional[str] = None,
    search_term: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Query entities with optional filters.
    
    Args:
        entity_type: Filter by entity type
        search_term: Search in entity name (ILIKE)
        limit: Maximum records
        offset: Pagination offset
        
    Returns:
        List of entity records
    """
    with postgres_session() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if entity_type and search_term:
                cur.execute(
                    _sql("SELECT_ENTITIES_BY_TYPE_AND_SEARCH"),
                    {
                        "entity_type": entity_type,
                        "search_term": f"%{search_term}%",
                        "limit": limit,
                        "offset": offset,
                    },
                )
            elif entity_type:
                cur.execute(
                    _sql("SELECT_ENTITIES_BY_TYPE"),
                    {"entity_type": entity_type, "limit": limit, "offset": offset},
                )
            elif search_term:
                cur.execute(
                    _sql("SELECT_ENTITIES_BY_SEARCH"),
                    {"search_term": f"%{search_term}%", "limit": limit, "offset": offset},
                )
            else:
                cur.execute(
                    _sql("SELECT_ALL_ENTITIES"),
                    {"limit": limit, "offset": offset},
                )
            
            rows = cur.fetchall()
    
    return [dict(row) for row in rows]


def get_entity_by_name(entity_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a single entity by exact name match.
    
    Args:
        entity_name: Entity name to find
        
    Returns:
        Entity record or None
    """
    with postgres_session() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(_sql("SELECT_ENTITY_BY_NAME"), {"entity_name": entity_name})
            row = cur.fetchone()
    
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Conversation History Operations
# ---------------------------------------------------------------------------
# UNUSED: These functions are not used by hrb_emp_lms MCP server.
# Services use SQLAlchemy ORM (database.py) instead of direct psycopg.
# TODO: Remove if agent memory features are not planned.


def insert_conversation_message(
    thread_id: str,
    role: str,
    content: str,
    user_id: Optional[str] = None,
    tool_calls: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Insert a conversation message for analytics/history.
    
    Note: This is for persistent storage, not STM (which uses SQLite).
    
    Args:
        thread_id: Conversation thread identifier
        role: Message role ('user', 'assistant', 'system', 'tool')
        content: Message content
        user_id: Optional user identifier
        tool_calls: Optional tool call data (JSON)
        
    Returns:
        Message ID (UUID)
    """
    message_id = str(uuid.uuid4())
    
    with postgres_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _sql("INSERT_CONVERSATION_MESSAGE"),
                {
                    "id": message_id,
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "role": role,
                    "content": content,
                    "tool_calls": psycopg.types.json.Json(tool_calls) if tool_calls else None,
                },
            )
    
    logger.debug("Inserted conversation message id=%s, thread=%s", message_id, thread_id)
    return message_id


def query_conversation_history(
    thread_id: str,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Query conversation history for a thread.
    
    Args:
        thread_id: Conversation thread identifier
        limit: Maximum messages
        offset: Pagination offset
        
    Returns:
        List of messages in chronological order
    """
    with postgres_session() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                _sql("SELECT_CONVERSATION_BY_THREAD"),
                {"thread_id": thread_id, "limit": limit, "offset": offset},
            )
            rows = cur.fetchall()
    
    return [dict(row) for row in rows]


def delete_conversation_thread(thread_id: str) -> int:
    """
    Delete all messages in a conversation thread.
    
    Args:
        thread_id: Thread identifier
        
    Returns:
        Number of messages deleted
    """
    with postgres_session() as conn:
        with conn.cursor() as cur:
            cur.execute(_sql("DELETE_CONVERSATION_BY_THREAD"), {"thread_id": thread_id})
            deleted = cur.rowcount
    
    if deleted:
        logger.info("Deleted %d messages from thread=%s", deleted, thread_id)
    
    return deleted

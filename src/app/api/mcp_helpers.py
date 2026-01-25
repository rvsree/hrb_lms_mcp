"""
MCP Helper Utilities.

This module provides utility functions and helpers for MCP operations.
These are reusable functions that support tool implementations but are not
themselves MCP tools.

Examples:
- Database session management helpers
- Response formatting utilities
- Validation helpers
- Error handling utilities
"""

from typing import Any, Dict, Optional
from contextlib import contextmanager

from src.app.repos.database import get_db
from src.app.common.config.app_logging import get_logger

logger = get_logger("mcp_helpers")


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    
    Ensures proper cleanup of database connections after tool execution.
    
    Usage:
        with get_db_session() as db:
            # Use db here
            pass
        # db is automatically closed
    """
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


def format_error_response(error: Exception, tool_name: str) -> Dict[str, Any]:
    """
    Format error response for MCP tools.
    
    Args:
        error: The exception that occurred
        tool_name: Name of the tool that failed
        
    Returns:
        Formatted error dictionary
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    logger.error(f"[MCP] Tool: {tool_name} error - {error_type}: {error_message}")
    
    return {
        "error": True,
        "error_type": error_type,
        "error_message": error_message,
        "tool": tool_name
    }


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """
    Validate that required fields are present in data.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        
    Raises:
        ValueError: If any required field is missing
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")


def sanitize_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize response data by removing sensitive information.
    
    Args:
        response: Response dictionary to sanitize
        
    Returns:
        Sanitized response dictionary
    """
    # Remove any sensitive fields if needed
    # For now, just return as-is, but this is where you'd filter sensitive data
    sensitive_fields = ["password", "ssn", "credit_card"]
    
    sanitized = response.copy()
    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = "***REDACTED***"
    
    return sanitized

"""
Health Check & Observability Endpoints.

Provides endpoints to verify connectivity and monitor:
- Application health
- PostgreSQL database connectivity
"""

from fastapi import APIRouter, HTTPException, status
from src.app.common.config.app_logging import get_logger
from src.app.common.providers_client.db_client.postgres_db_client import postgres_health_check

logger = get_logger("health")

health_router = APIRouter(prefix="/hrb_emp_lms/health", tags=["health"])


@health_router.get("/app", summary="Application health")
async def app_health():
    """
    Basic app health endpoint.
    """
    return {
        "status": "healthy",
        "message": "Application is running.",
    }


@health_router.get("/postgres", summary="PostgreSQL health")
async def postgres_health():
    """
    Check PostgreSQL database connection.
    
    Verifies connectivity to the PostgreSQL database used by the MCP server
    for leave management data (employees, leave balances, leave requests, HITL requests).
    """
    status_obj = postgres_health_check()
    if status_obj["status"] != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=status_obj,
        )
    return {
        "status": "healthy",
        "message": "PostgreSQL is reachable.",
        "data": status_obj,
    }



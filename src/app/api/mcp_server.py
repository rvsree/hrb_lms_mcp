"""
MCP Server Configuration and Setup.

This module initializes the FastMCP server instance with proper configuration
and middleware. It follows MCP best practices for modular server architecture.

The FastMCP server is configured for:
- Stateless HTTP mode (no session ID required)
- JSON responses (simpler for HTTP clients)
- Request logging middleware
"""

import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from mcp.server.fastmcp import FastMCP
from src.app.common.config.app_logging import get_logger

logger = get_logger("mcp_server")

# Initialize FastMCP server instance
# This is the central MCP server instance that will be used by all tools
mcp = FastMCP("lms")

# Configure FastMCP for stateless HTTP and JSON responses
# Stateless mode: No session ID required, creates new transport per request
# JSON responses: Returns JSON instead of SSE streams (simpler for HTTP clients)
mcp.settings.stateless_http = True
mcp.settings.json_response = True

if logging.getLogger().isEnabledFor(logging.INFO):
    logger.info("[MCP] FastMCP server initialized - stateless_http=True, json_response=True")


class MCPRequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log MCP requests and tool calls for observability."""
    
    async def dispatch(self, request: Request, call_next):
        """Log incoming MCP requests with payload details."""
        if request.method == "POST" and request.url.path == "/mcp":
            try:
                body = await request.body()
                if body:
                    try:
                        payload = json.loads(body)
                        method = payload.get("method", "unknown")
                        request_id = payload.get("id", "unknown")
                        
                        if method == "tools/call":
                            tool_name = payload.get("params", {}).get("name", "unknown")
                            arguments = payload.get("params", {}).get("arguments", {})
                            logger.info(
                                f"[MCP] tools/call request - "
                                f"tool_name={tool_name}, "
                                f"arguments={arguments}, "
                                f"request_id={request_id}"
                            )
                        elif method == "tools/list":
                            logger.info(f"[MCP] tools/list request received - request_id={request_id}")
                        
                        # Recreate request with body for downstream processing
                        async def receive():
                            return {"type": "http.request", "body": body}
                        
                        request._receive = receive
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                logger.debug(f"[MCP] Error logging request: {e}")
        
        response = await call_next(request)
        return response


def create_mcp_app():
    """
    Create and configure the FastMCP streamable HTTP app.
    
    This function sets up the FastMCP application with:
    - JSON-RPC 2.0 protocol handling (automatic via streamable_http_app)
    - Request logging middleware
    - Health check endpoints (mounted separately since FastMCP doesn't support FastAPI routers)
    
    Returns:
        FastMCP streamable HTTP application instance
    """
    # Use FastMCP's streamable-http app directly
    # This handles JSON-RPC 2.0 protocol automatically
    app = mcp.streamable_http_app()
    
    # Add request logging middleware for observability
    app.add_middleware(MCPRequestLoggingMiddleware)
    
    # Mount health endpoints using Starlette's mount functionality
    # Since FastMCP uses Starlette, we can mount a separate app for health checks
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from src.app.common.providers_client.db_client.postgres_db_client import postgres_health_check
    
    async def app_health(request):
        """Application health endpoint."""
        return JSONResponse({
            "status": "healthy",
            "message": "Application is running.",
        })
    
    async def postgres_health(request):
        """PostgreSQL database health endpoint."""
        status_obj = postgres_health_check()
        if status_obj["status"] != "healthy":
            return JSONResponse(
                status_obj,
                status_code=503
            )
        return JSONResponse({
            "status": "healthy",
            "message": "PostgreSQL is reachable.",
            "data": status_obj,
        })
    
    # Create health app with routes
    health_app = Starlette(routes=[
        Route("/app", app_health, methods=["GET"]),
        Route("/postgres", postgres_health, methods=["GET"]),
    ])
    
    # Mount health app at /hrb_emp_lms/health
    app.mount("/hrb_emp_lms/health", health_app)
    
    if logging.getLogger().isEnabledFor(logging.INFO):
        logger.info("[MCP] FastMCP streamable HTTP app created with logging middleware and health endpoints")
    
    return app


# Create the app instance
# This will be imported by main.py and tools will register themselves via @mcp.tool()
app = create_mcp_app()

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
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from src.app.common.auth.token_service import create_access_token, verify_client_credentials
from src.app.common.config.app_logging import get_logger

logger = get_logger("mcp_server")

# Initialize FastMCP server instance
# This is the central MCP server instance that will be used by all tools
#
# transport_security: FastMCP's constructor auto-enables DNS rebinding
# protection (Host-header allowlisting) whenever its own `host` param
# defaults to "127.0.0.1" - which it does here, since main.py binds
# uvicorn to 0.0.0.0 directly and never tells FastMCP that. That
# allowlist only ever contains localhost/127.0.0.1, so any real deployed
# hostname (the raw *.awsapprunner.com URL, or a custom domain) gets
# rejected with 421 "Invalid Host header" - found 2026-10-07 wiring real
# AWS connectivity (see hrb_chatbot_v2's RAG-ROADMAP.md Phase 118).
# DNS-rebinding protection exists to stop a malicious website's browser
# JS from reaching a local-only dev server via a rebound DNS name - not a
# concern for this server, which is never localhost-only in any real
# environment and already requires a real Bearer JWT (BearerAuthMiddleware
# below) on every /mcp call. Disabled explicitly rather than guessing at
# an allowed_hosts list that would need updating every time this server
# gets a new domain.
mcp = FastMCP("lms", transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))

# Configure FastMCP for stateless HTTP and JSON responses
# Stateless mode: No session ID required, creates new transport per request
# JSON responses: Returns JSON instead of SSE streams (simpler for HTTP clients)
mcp.settings.stateless_http = True
mcp.settings.json_response = True

# if logging.getLogger().isEnabledFor(logging.INFO):
#     logger.info("[MCP] FastMCP server initialized - stateless_http=True, json_response=True")


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


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Rejects POST /mcp requests with no valid Bearer JWT (2026-09-22) -
    replaces the X-API-Key check that was configured but never actually
    enforced anywhere in this codebase. /oauth/token and the health
    endpoints stay open - a client needs to call /oauth/token before it
    has a token to present."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path == "/mcp":
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse({"error": "Missing Bearer token"}, status_code=401)

            token = auth_header.removeprefix("Bearer ")
            try:
                jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                return JSONResponse({"error": "Token expired"}, status_code=401)
            except jwt.PyJWTError:
                return JSONResponse({"error": "Invalid token"}, status_code=401)

        return await call_next(request)


def _jwt_secret() -> str:
    from src.app.common.config.config import settings
    return settings.jwt_secret_key


async def issue_token(request: Request):
    """POST /oauth/token - client_credentials grant. Body:
    {"client_id": "...", "client_secret": "..."}."""
    body = await request.json()
    client_id = body.get("client_id")
    client_secret = body.get("client_secret")

    if not client_id or not client_secret:
        return JSONResponse({"error": "client_id and client_secret are required"}, status_code=400)

    scopes = verify_client_credentials(client_id, client_secret)
    if scopes is None:
        return JSONResponse({"error": "invalid_client"}, status_code=401)

    access_token, expires_in = create_access_token(client_id, scopes)
    return JSONResponse({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": " ".join(scopes),
    })


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

    # Bearer-token auth on /mcp (2026-09-22) - added after (so it runs
    # before, Starlette middleware order) the logging middleware, so an
    # unauthenticated request is rejected before its body is even logged.
    app.add_middleware(BearerAuthMiddleware)

    # Mount health endpoints using Starlette's mount functionality
    # Since FastMCP uses Starlette, we can mount a separate app for health checks
    from starlette.applications import Starlette
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

    # Mount the OAuth2 token endpoint - open, no auth required to reach it
    # (a client needs a token from here before it has one to present).
    oauth_app = Starlette(routes=[Route("/token", issue_token, methods=["POST"])])
    app.mount("/oauth", oauth_app)
    
    # if logging.getLogger().isEnabledFor(logging.INFO):
    #     logger.info("[MCP] FastMCP streamable HTTP app created with logging middleware and health endpoints")
    
    return app


# Create the app instance
# This will be imported by main.py and tools will register themselves via @mcp.tool()
app = create_mcp_app()

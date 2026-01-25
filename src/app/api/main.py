"""
Main entry point for HRB Employee LMS MCP Server.

Pure FastMCP implementation - no FastAPI wrapper.
FastMCP handles JSON-RPC 2.0 protocol automatically via streamable-http transport.

Run with: python -m src.app.api.main
Or: uvicorn src.app.api.main:app --host 0.0.0.0 --port 8190
"""

import os
import json
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.app.common.config.app_logging import setup_logging, get_logger
from src.app.common.config.config import settings

# Import FastMCP instance from tools module
from src.app.api.controller.lms_mcp_tools import mcp

# Setup logging
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
log_level = settings.get_log_level()
component_levels = settings.get_component_log_levels()
environ = settings.environ

setup_logging(level=log_level, use_colors=True, component_levels=component_levels)
logger = get_logger("app_main")

if log_level <= logging.INFO:
    logger.info(f"HRB Employee LMS MCP Server - Environ: {environ}, Log level: {logging.getLevelName(log_level)}")


class MCPRequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log MCP requests and tool calls."""
    
    async def dispatch(self, request: Request, call_next):
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
                            logger.info(f"[MCP] tools/call request - tool_name={tool_name}, arguments={arguments}, request_id={request_id}")
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


# Use FastMCP's streamable-http app directly
# This handles JSON-RPC 2.0 protocol automatically
app = mcp.streamable_http_app()

# Add request logging middleware
app.add_middleware(MCPRequestLoggingMiddleware)

if log_level <= logging.INFO:
    logger.info("HRB Employee LMS MCP Server initialized with Pure FastMCP (streamable-http)")


def main():
    """Main entry point to run the server."""
    log_level = settings.get_log_level()
    log_level_name = logging.getLevelName(log_level).lower()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.server_port,
        log_level=log_level_name,
        log_config=None
    )


if __name__ == "__main__":
    main()

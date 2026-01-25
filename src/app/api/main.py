"""
Main entry point for HRB Employee LMS MCP Server.

Pure FastMCP implementation - no FastAPI wrapper.
FastMCP handles JSON-RPC 2.0 protocol automatically via streamable-http transport.

This module follows modular MCP architecture:
- mcp_server.py: FastMCP server instance and configuration
- lms_mcp_tools.py: Tool definitions (imported here to register tools)
- mcp_helpers.py: Utility functions
- main.py: Entry point (this file)

Run with: python -m src.app.api.main
Or: uvicorn src.app.api.main:app --host 0.0.0.0 --port 8190
"""

import os
import logging
import uvicorn
from dotenv import load_dotenv

from src.app.common.config.app_logging import setup_logging, get_logger
from src.app.common.config.config import settings

# Import the FastMCP app from mcp_server module
# This ensures tools are registered before the app is used
from src.app.api.mcp_server import app

# Import tools module to register all tools with the FastMCP server
# Tools are registered via @mcp.tool() decorators when this module is imported
import src.app.api.controller.lms_mcp_tools  # noqa: F401

# Setup logging
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
log_level = settings.get_log_level()
component_levels = settings.get_component_log_levels()
environ = settings.environ

setup_logging(level=log_level, use_colors=True, component_levels=component_levels)
logger = get_logger("app_main")

if log_level <= logging.INFO:
    logger.info(f"HRB Employee LMS MCP Server - Environ: {environ}, Log level: {logging.getLevelName(log_level)}")
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

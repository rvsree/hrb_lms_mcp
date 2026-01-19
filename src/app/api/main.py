"""
Main entry point for HRB Employee LMS MCP Server.

This is the consolidated main.py that starts the FastAPI application.
Run with: python -m src.app.api.main
Or: uvicorn src.app.api.main:app --host 0.0.0.0 --port 8081
"""

import os
import sys
import logging
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api.admin.health import health_router
from src.app.api.controller.mcp_controller import mcp_router
from src.app.common.config.app_logging import setup_logging, get_logger
from src.app.common.config.config import settings


# IMPORTANT: Setup logging BEFORE anything else to ensure colors work
# This must happen at module import time so uvicorn uses our logging config
load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)

# Determine log level based on environ (dev -> INFO, release -> WARNING)
# Can be overridden by LOG_LEVEL environment variable
log_level = settings.get_log_level()
component_levels = settings.get_component_log_levels()
environ = settings.environ

# Setup logging immediately - this must happen before any other imports that use logging
setup_logging(level=log_level, use_colors=True, component_levels=component_levels)
logger = get_logger("app_main")

# Log the configuration (only if level allows)
if log_level <= logging.INFO:
    logger.info(f"HRB Employee LMS MCP Server - Environ: {environ}, Log level: {logging.getLevelName(log_level)}")

# Create FastAPI app
app = FastAPI(
    title="HRB Employee LMS MCP Server",
    version="1.0.0",
    description="Python-based MCP server for Leave Management System"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Routers
app.include_router(health_router)
app.include_router(mcp_router)

# Log initialization (only if level allows)
if log_level <= logging.INFO:
    logger.info("HRB Employee LMS MCP Server initialized")


@app.on_event("startup")
async def on_startup():
    """Re-apply logging configuration on startup to ensure uvicorn uses our colors."""
    # Re-setup logging to ensure uvicorn doesn't override our configuration
    log_level = settings.get_log_level()
    component_levels = settings.get_component_log_levels()
    setup_logging(level=log_level, use_colors=True, component_levels=component_levels)
    
    # Log startup completion (only if level allows)
    if log_level <= logging.INFO:
        environ = settings.environ
        logger.info(f"Logging configuration re-applied on startup. Environ: {environ}, Log level: {logging.getLevelName(log_level)}")
    else:
        logger.warning("Logging configuration re-applied on startup.")


def main():
    """Main entry point to run the server."""
    # Configure uvicorn to use our logging setup
    # log_config=None means uvicorn won't configure its own logging
    log_level = settings.get_log_level()
    log_level_name = logging.getLevelName(log_level).lower()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.server_port,
        log_level=log_level_name,
        log_config=None  # Use our custom logging configuration
    )


if __name__ == "__main__":
    main()



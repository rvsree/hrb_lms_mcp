import os
import logging
import uvicorn
from dotenv import load_dotenv
from src.app.common.config.app_logging import setup_logging, get_logger
from src.app.common.config.config import settings
from src.app.api.mcp_server import app
import src.app.api.controller.lms_mcp_tools  # noqa: F401

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

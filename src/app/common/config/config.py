"""Configuration management for hrb_emp_lms."""

import os
import logging
from typing import Optional, Dict
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    postgres_db_host: str = os.getenv("POSTGRES_DB_HOST", "localhost")
    postgres_db_port: int = int(os.getenv("POSTGRES_DB_PORT", "5432"))
    postgres_db_name: str = os.getenv("POSTGRES_DB_NAME", "coco")
    postgres_db_user: str = os.getenv("POSTGRES_DB_USER", "postgres")
    postgres_db_password: str = os.getenv("POSTGRES_DB_PASSWORD", "Igates_71")
    
    # Server
    server_port: int = int(os.getenv("SERVER_PORT", "8081"))
    api_key: str = os.getenv("API_KEY", "default-api-key")
    
    # Environment
    environ: str = os.getenv("APP_ENVIRON", "dev")  # dev or release
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "")  # Empty means auto-determine from environ
    
    @property
    def database_url(self) -> str:
        """
        Get database URL.
        Uses get_postgres_dsn() to ensure consistency with postgres_db_client.
        This ensures both SQLAlchemy (database.py) and psycopg (postgres_db_client.py)
        use the same connection string with SSL mode and other settings.
        """
        from src.app.common.providers_config.db_config.postgres_db_config import get_postgres_dsn
        return get_postgres_dsn()
    
    def get_log_level(self) -> int:
        """
        Determine log level based on environ or LOG_LEVEL environment variable.
        
        Priority:
        1. LOG_LEVEL environment variable (if set, takes precedence)
        2. environ value:
           - "dev" -> logging.INFO (shows DEBUG, INFO, WARNING, ERROR)
           - "release" -> logging.WARNING (shows WARNING, ERROR only)
        
        Returns:
            int: Logging level constant (logging.INFO, logging.WARNING, etc.)
        """
        # Check if LOG_LEVEL is explicitly set (takes precedence)
        log_level_str = os.getenv("LOG_LEVEL", "").upper()
        if log_level_str:
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "WARN": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL,
            }
            if log_level_str in level_map:
                return level_map[log_level_str]
        
        # Otherwise, determine based on environ
        environ = self.environ.lower()
        if environ == "release":
            return logging.WARNING
        else:
            # Default to INFO for "dev" or any other value
            return logging.INFO
    
    def get_component_log_levels(self) -> Dict[str, int]:
        """
        Get component-specific log levels based on environ.
        
        For "release" environ, sets stricter levels for noisy components:
        - uvicorn, fastapi: WARNING (to reduce startup logs)
        - mcp_controller: WARNING (to reduce MCP request logs)
        
        For "dev" environ, uses the root log level for all components.
        
        Returns:
            dict: Mapping of component names to log levels
        """
        root_level = self.get_log_level()
        environ = self.environ.lower()
        
        # Default: all components use root level
        component_levels = {
            'uvicorn': root_level,
            'uvicorn.access': root_level,
            'uvicorn.error': root_level,
            'fastapi': root_level,
            'mcp_controller': root_level,
        }
        
        # For release mode, set stricter levels for noisy components
        if environ == "release":
            component_levels.update({
                'uvicorn': logging.WARNING,
                'uvicorn.access': logging.WARNING,
                'uvicorn.error': logging.WARNING,
                'fastapi': logging.WARNING,
                'mcp_controller': logging.WARNING,  # Reduce MCP INFO logs
            })
        
        return component_levels

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


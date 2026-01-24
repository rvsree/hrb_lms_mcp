"""
MCP Server for Leave Management System.

This module implements the MCP server that handles tool listing and execution.
It uses the tool registry from lms_mcp_tools for tool management.
"""

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from src.app.repos.database import get_db
from src.app.api.controller.lms_mcp_tools import tool_registry
from src.app.exceptions.exceptions import BusinessException, ResourceNotFoundException
from src.app.common.config.app_logging import get_logger

logger = get_logger("lms_mcp_server")


class LMSMCPServer:
    """
    MCP Server for Leave Management System.
    
    This server implements the MCP protocol over HTTP transport.
    It manages tool registration, listing, and execution.
    """
    
    # MCP Protocol Version
    MCP_PROTOCOL_VERSION = "1.0"
    MCP_JSONRPC_VERSION = "2.0"
    MCP_TRANSPORT_TYPE = "http"
    
    def __init__(self):
        """Initialize the MCP server."""
        self.tool_registry = tool_registry
        logger.info("[MCP] Server: Initialized LMS MCP Server")
        logger.info(f"[MCP] Server: Protocol version={self.MCP_PROTOCOL_VERSION}, Transport={self.MCP_TRANSPORT_TYPE}")
    
    def list_tools(self) -> Dict[str, Any]:
        """
        List all available MCP tools.
        
        Returns:
            Dictionary with tools list in MCP format:
            {
                "tools": [
                    {
                        "name": "tool_name",
                        "description": "Tool description",
                        "inputSchema": {...}
                    },
                    ...
                ]
            }
        """
        tools = self.tool_registry.list_tools()
        logger.info(f"[MCP] Server: Listed {len(tools)} tools")
        return {"tools": tools}
    
    def call_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any], 
        api_key: Optional[str] = None
    ) -> Any:
        """
        Execute an MCP tool.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments dictionary
            api_key: API key for tool-level validation (optional, for tool-level auth)
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found or validation fails
            BusinessException: If business logic error occurs
            ResourceNotFoundException: If resource not found
        """
        logger.info(f"[MCP] Server: Executing tool '{tool_name}'")
        logger.debug(f"[MCP] Server: Tool arguments: {arguments}")
        
        # Check if tool exists
        tool_def = self.tool_registry.get_tool(tool_name)
        if not tool_def:
            error_msg = f"Unknown tool: {tool_name}"
            logger.error(f"[MCP] Server: {error_msg}")
            return {
                "error": error_msg,
                "status": "error",
                "error_type": "tool_not_found"
            }
        
        # Tool-level API key validation (if tool requires it)
        if tool_def.requires_api_key:
            if not api_key:
                error_msg = f"API key required for tool '{tool_name}'"
                logger.warning(f"[MCP] Server: {error_msg}")
                return {
                    "error": error_msg,
                    "status": "error",
                    "error_type": "authentication_error"
                }
            
            # Validate API key (using settings from config)
            from src.app.common.config.config import settings
            if api_key != settings.api_key:
                error_msg = f"Invalid API key for tool '{tool_name}'"
                logger.warning(f"[MCP] Server: {error_msg}")
                return {
                    "error": error_msg,
                    "status": "error",
                    "error_type": "authentication_error"
                }
            
            logger.debug(f"[MCP] Server: Tool-level API key validated for '{tool_name}'")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Execute tool via registry
            result = self.tool_registry.execute_tool(tool_name, arguments, db)
            
            logger.info(f"[MCP] Server: Tool '{tool_name}' executed successfully")
            return result
            
        except ValueError as e:
            # Validation or tool not found errors
            error_msg = str(e)
            logger.error(f"[MCP] Server: Tool '{tool_name}' validation error - {error_msg}")
            return {
                "error": error_msg,
                "status": "error",
                "error_type": "validation_error"
            }
            
        except (BusinessException, ResourceNotFoundException) as e:
            # Business logic errors
            error_msg = str(e)
            logger.error(f"[MCP] Server: Tool '{tool_name}' business error - {error_msg}")
            return {
                "error": error_msg,
                "status": "error",
                "error_type": "business_error"
            }
            
        except Exception as e:
            # Unexpected errors
            error_msg = str(e)
            logger.exception(f"[MCP] Server: Tool '{tool_name}' execution error - {error_msg}")
            return {
                "error": error_msg,
                "status": "error",
                "error_type": "internal_error"
            }
            
        finally:
            # Always close database session
            db.close()
            logger.debug(f"[MCP] Server: Database session closed for tool '{tool_name}'")
    
    def get_protocol_info(self) -> Dict[str, Any]:
        """
        Get MCP protocol information.
        
        Returns:
            Dictionary with protocol metadata
        """
        return {
            "protocol_version": self.MCP_PROTOCOL_VERSION,
            "jsonrpc_version": self.MCP_JSONRPC_VERSION,
            "transport": self.MCP_TRANSPORT_TYPE,
            "server_name": "LMS MCP Server",
            "tools_count": len(self.tool_registry.list_tools())
        }


# Global server instance (singleton pattern)
_server_instance: LMSMCPServer = None


def get_mcp_server() -> LMSMCPServer:
    """
    Get or create the global MCP server instance.
    
    Returns:
        LMSMCPServer instance
    """
    global _server_instance
    if _server_instance is None:
        _server_instance = LMSMCPServer()
    return _server_instance

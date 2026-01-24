"""
MCP Controller with JSON-RPC 2.0 endpoint.

This controller handles HTTP transport for MCP (Model Context Protocol) server.
It implements MCP protocol over HTTP/REST, maintaining backward compatibility
with existing clients.

MCP Protocol Compliance:
- Protocol Version: 1.0
- JSON-RPC Version: 2.0
- Transport: HTTP/REST
- Authentication: API Key (endpoint-level + tool-level)
"""

import uuid
from typing import Any, Dict, Optional, Tuple
from fastapi import APIRouter, Header, Response
from fastapi.responses import JSONResponse

from src.app.models.mcp_request import McpRequest
from src.app.models.mcp_response import McpResponse
from src.app.models.mcp_error import McpError
from src.app.api.controller.lms_mcp_server import get_mcp_server
from src.app.common.config.config import settings
from src.app.common.config.app_logging import get_logger

logger = get_logger("mcp_controller")

# Create router instead of FastAPI app
mcp_router = APIRouter(prefix="/api/hrb/lms", tags=["mcp"])


# ============================================================================
# Helper Functions
# ============================================================================

def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """
    Verify API key.
    
    Args:
        x_api_key: API key from header
        
    Returns:
        True if API key is valid, False otherwise
    """
    if not x_api_key:
        return False
    return x_api_key == settings.api_key


def add_mcp_protocol_headers(response: Response, mcp_server) -> None:
    """
    Add MCP protocol headers to HTTP response.
    
    Args:
        response: FastAPI Response object
        mcp_server: MCP server instance
    """
    if response:
        response.headers["X-MCP-Version"] = mcp_server.MCP_PROTOCOL_VERSION
        response.headers["X-MCP-Transport"] = mcp_server.MCP_TRANSPORT_TYPE
        response.headers["X-MCP-JSONRPC-Version"] = mcp_server.MCP_JSONRPC_VERSION
        logger.debug(f"[MCP] Headers: Added MCP protocol headers to response")


def validate_mcp_request(request: McpRequest, request_id: str) -> Optional[McpResponse]:
    """
    Validate MCP request (JSON-RPC version and method).
    
    Args:
        request: MCP request object
        request_id: Request ID
        
    Returns:
        McpResponse with error if validation fails, None if valid
    """
    # Validate JSON-RPC version
    if request.jsonrpc != "2.0":
        logger.warning(f"[MCP] [VALIDATION] Invalid JSON-RPC version: {request.jsonrpc}")
        return McpResponse(
            id=request_id,
            error=McpError(
                code=-32600,
                message="Invalid Request",
                data="jsonrpc must be '2.0'"
            )
        )
    
    # Validate method
    if not request.method:
        logger.warning(f"[MCP] [VALIDATION] Missing method in request")
        return McpResponse(
            id=request_id,
            error=McpError(
                code=-32600,
                message="Invalid Request",
                data="method is required"
            )
        )
    
    return None  # Validation passed


def create_unauthorized_response(request_id: str) -> JSONResponse:
    """
    Create unauthorized response for invalid API key.
    
    Args:
        request_id: Request ID
        
    Returns:
        JSONResponse with 401 status and error
    """
    return JSONResponse(
        status_code=401,
        content={
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": "Unauthorized",
                "data": "Invalid API key"
            }
        }
    )


def handle_tools_list(mcp_server, request_id: str) -> Dict[str, Any]:
    """
    Handle tools/list method.
    
    Args:
        mcp_server: MCP server instance
        request_id: Request ID
        
    Returns:
        Tools list result
    """
    logger.info(f"[MCP] [TOOLS] Listing all available MCP tools")
    result = mcp_server.list_tools()
    tools_count = len(result.get("tools", [])) if isinstance(result, dict) else 0
    logger.info(f"[MCP] [TOOLS] Listed {tools_count} tools successfully")
    return result


def handle_tools_call(
    mcp_server,
    request: McpRequest,
    request_id: str,
    api_key: Optional[str]
) -> Tuple[Optional[Dict[str, Any]], Optional[McpResponse]]:
    """
    Handle tools/call method.
    
    Args:
        mcp_server: MCP server instance
        request: MCP request object
        request_id: Request ID
        api_key: API key for tool-level validation
        
    Returns:
        Tuple of (result, error_response)
        - If successful: (result, None)
        - If error: (None, McpResponse with error)
    """
    # Validate params
    if not request.params:
        error_msg = "params is required for tools/call"
        logger.error(f"[MCP] [ERROR] {error_msg}")
        return None, McpResponse(
            id=request_id,
            error=McpError(
                code=-32602,
                message="Invalid Params",
                data=error_msg
            )
        )
    
    tool_name = request.params.get("name")
    if not tool_name:
        error_msg = "params.name is required"
        logger.error(f"[MCP] [ERROR] {error_msg}")
        return None, McpResponse(
            id=request_id,
            error=McpError(
                code=-32602,
                message="Invalid Params",
                data=error_msg
            )
        )
    
    arguments = request.params.get("arguments", {})
    
    # Log tool call with payload
    logger.info(f"[MCP] [TOOL_CALL] Executing tool: {tool_name}")
    logger.info(f"[MCP] [TOOL_CALL] Tool arguments/payload: {arguments}")
    
    # Execute tool via MCP server (pass API key for tool-level validation)
    result = mcp_server.call_tool(tool_name, arguments, api_key=api_key)
    
    # Log tool result
    log_tool_result(tool_name, result)
    
    return result, None


def log_tool_result(tool_name: str, result: Any) -> None:
    """
    Log tool execution result.
    
    Args:
        tool_name: Name of the tool executed
        result: Tool execution result
    """
    if isinstance(result, dict):
        if result.get("error") or result.get("status") == "error":
            error_msg = result.get("error", "Unknown error")
            logger.error(f"[MCP] [TOOL_RESULT] Tool '{tool_name}' returned error: {error_msg}")
        else:
            logger.info(f"[MCP] [TOOL_RESULT] Tool '{tool_name}' executed successfully")
            # Log result summary (truncate if too large)
            result_str = str(result)
            if len(result_str) > 500:
                logger.info(f"[MCP] [TOOL_RESULT] Result (truncated): {result_str[:500]}...")
            else:
                logger.info(f"[MCP] [TOOL_RESULT] Result: {result}")
    else:
        logger.info(f"[MCP] [TOOL_RESULT] Tool '{tool_name}' returned result (type: {type(result).__name__})")


def create_success_response(request_id: str, result: Any) -> McpResponse:
    """
    Create successful MCP response.
    
    Args:
        request_id: Request ID
        result: Result data
        
    Returns:
        McpResponse with result
    """
    # Log response summary
    if isinstance(result, dict):
        result_summary = f"result_type=dict, keys={list(result.keys())[:5]}"
        logger.info(f"[MCP] [RESPONSE] Response summary: {result_summary}")
    else:
        logger.info(f"[MCP] [RESPONSE] Response type: {type(result).__name__}")
    
    return McpResponse(
        id=request_id,
        result=result
    )


def create_error_response(request_id: str, error_code: int, error_message: str, error_data: Any = None) -> McpResponse:
    """
    Create error MCP response.
    
    Args:
        request_id: Request ID
        error_code: JSON-RPC error code
        error_message: Error message
        error_data: Additional error data
        
    Returns:
        McpResponse with error
    """
    return McpResponse(
        id=request_id,
        error=McpError(
            code=error_code,
            message=error_message,
            data=error_data
        )
    )


# ============================================================================
# Main Endpoint Handler
# ============================================================================

@mcp_router.post(
    "/mcp",
    response_model=McpResponse,
    summary="MCP Protocol Endpoint (HTTP Transport)",
    description="""
    MCP (Model Context Protocol) endpoint over HTTP transport.
    
    **Protocol Information:**
    - Protocol Version: 1.0
    - JSON-RPC Version: 2.0
    - Transport: HTTP/REST
    - Authentication: API Key (X-API-Key header)
    
    **Supported Methods:**
    - `tools/list`: Returns list of available tools with JSON schemas
    - `tools/call`: Executes a tool by name with arguments
    
    **MCP Compliance:**
    This endpoint implements MCP protocol over HTTP, allowing remote clients
    to access MCP tools via standard HTTP requests. The implementation follows
    MCP protocol specification with JSON-RPC 2.0 messaging.
    """
)
async def handle_mcp_request(
    request: McpRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    response: Response = None
):
    """
    MCP JSON-RPC 2.0 endpoint handler.
    
    This endpoint implements MCP protocol over HTTP transport.
    API key validation is performed at endpoint level (all tools require authentication).
    """
    # Generate request ID
    request_id = request.id or str(uuid.uuid4())
    
    # Authenticate request
    if not verify_api_key(x_api_key):
        logger.warning(f"[MCP] [AUTH] Invalid API key attempt - request_id={request_id}")
        return create_unauthorized_response(request_id)
    
    logger.info(f"[MCP] [AUTH] API key verified successfully")
    
    # Get MCP server instance
    mcp_server = get_mcp_server()
    
    # Add MCP protocol headers to response
    add_mcp_protocol_headers(response, mcp_server)
    
    # Log incoming request
    log_incoming_request(request, request_id)
    
    try:
        # Validate request
        validation_error = validate_mcp_request(request, request_id)
        if validation_error:
            return validation_error
        
        # Route to appropriate handler based on method
        result = None
        
        if request.method == "tools/list":
            result = handle_tools_list(mcp_server, request_id)
            
        elif request.method == "tools/call":
            result, error_response = handle_tools_call(mcp_server, request, request_id, x_api_key)
            if error_response:
                return error_response
                
        else:
            # Unknown method
            logger.warning(f"[MCP] [ERROR] Unknown method: {request.method}")
            return create_error_response(
                request_id=request_id,
                error_code=-32601,
                error_message="Method Not Found",
                error_data=f"Unknown method: {request.method}"
            )
        
        # Create and return success response
        logger.info(f"[MCP] [RESPONSE] Request completed successfully - method={request.method}, id={request_id}, status=success")
        return create_success_response(request_id, result)
        
    except Exception as e:
        # Handle unexpected errors
        error_msg = str(e)
        logger.error(f"[MCP] [ERROR] Error processing MCP request: {error_msg}", exc_info=True)
        logger.error(f"[MCP] [RESPONSE] Request failed - method={request.method}, id={request_id}, status=error, error={error_msg}")
        
        return create_error_response(
            request_id=request_id,
            error_code=-32603,
            error_message="Internal Error",
            error_data=error_msg
        )


def log_incoming_request(request: McpRequest, request_id: str) -> None:
    """
    Log incoming MCP request details.
    
    Args:
        request: MCP request object
        request_id: Request ID
    """
    logger.info(f"[MCP] [REQUEST] Incoming MCP request - method={request.method}, id={request_id}")
    logger.info(f"[MCP] [REQUEST] JSON-RPC version: {request.jsonrpc}")
    if request.params:
        logger.info(f"[MCP] [REQUEST] Parameters: {request.params}")


# ============================================================================
# Deprecated Functions - REMOVED
# ============================================================================
# The following functions have been removed after migration period:
# - list_tools() - Use mcp_server.list_tools() instead
# - call_tool() - Use mcp_server.call_tool() instead
#
# All code should now use the MCP server instance directly.




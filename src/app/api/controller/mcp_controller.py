"""MCP Controller with JSON-RPC 2.0 endpoint."""

import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.app.repos.database import get_db
from src.app.services.leave_balance_service import LeaveBalanceService
from src.app.services.leave_request_service import LeaveRequestService
from src.app.services.hitl_service import HitlService
from src.app.exceptions.exceptions import BusinessException, ResourceNotFoundException
from src.app.common.config.config import settings
from src.app.common.config.app_logging import get_logger

logger = get_logger("mcp_controller")

# Create router instead of FastAPI app
mcp_router = APIRouter(prefix="/api/hrb/lms", tags=["mcp"])


# Pydantic models for JSON-RPC 2.0
class McpRequest(BaseModel):
    """JSON-RPC 2.0 request."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class McpError(BaseModel):
    """JSON-RPC 2.0 error."""
    code: int
    message: str
    data: Optional[Any] = None


class McpResponse(BaseModel):
    """JSON-RPC 2.0 response."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[McpError] = None


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """Verify API key."""
    if not x_api_key:
        return False
    return x_api_key == settings.api_key


@mcp_router.post("/mcp", response_model=McpResponse)
async def handle_mcp_request(
    request: McpRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    MCP JSON-RPC 2.0 endpoint.
    
    Supports:
    - tools/list: Returns list of available tools with JSON schemas
    - tools/call: Executes a tool by name with arguments
    """
    # Verify API key
    if not verify_api_key(x_api_key):
        request_id_temp = request.id or str(uuid.uuid4())
        logger.warning(f"[MCP] [AUTH] Invalid API key attempt - request_id={request_id_temp}")
        return JSONResponse(
            status_code=401,
            content={
                "jsonrpc": "2.0",
                "id": request_id_temp,
                "error": {
                    "code": -32000,
                    "message": "Unauthorized",
                    "data": "Invalid API key"
                }
            }
        )
    
    logger.info(f"[MCP] [AUTH] API key verified successfully")
    
    request_id = request.id or str(uuid.uuid4())
    
    # Log incoming request with full details
    logger.info(f"[MCP] [REQUEST] Incoming MCP request - method={request.method}, id={request_id}")
    logger.info(f"[MCP] [REQUEST] JSON-RPC version: {request.jsonrpc}")
    if request.params:
        logger.info(f"[MCP] [REQUEST] Parameters: {request.params}")
    
    try:
        # Validate JSON-RPC version
        if request.jsonrpc != "2.0":
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
            return McpResponse(
                id=request_id,
                error=McpError(
                    code=-32600,
                    message="Invalid Request",
                    data="method is required"
                )
            )
        
        # Handle different methods
        result = None
        if request.method == "tools/list":
            logger.info(f"[MCP] [TOOLS] Listing all available MCP tools")
            result = list_tools()
            tools_count = len(result.get("tools", [])) if isinstance(result, dict) else 0
            logger.info(f"[MCP] [TOOLS] Listed {tools_count} tools successfully")
        elif request.method == "tools/call":
            if not request.params:
                error_msg = "params is required for tools/call"
                logger.error(f"[MCP] [ERROR] {error_msg}")
                return McpResponse(
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
                return McpResponse(
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
            
            result = call_tool(tool_name, arguments)
            
            # Log tool result
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
        else:
            return McpResponse(
                id=request_id,
                error=McpError(
                    code=-32601,
                    message="Method Not Found",
                    data=f"Unknown method: {request.method}"
                )
            )
        
        # Log successful response
        logger.info(f"[MCP] [RESPONSE] Request completed successfully - method={request.method}, id={request_id}, status=success")
        response = McpResponse(
            id=request_id,
            result=result
        )
        
        # Log response summary
        if isinstance(result, dict):
            result_summary = f"result_type=dict, keys={list(result.keys())[:5]}"
            logger.info(f"[MCP] [RESPONSE] Response summary: {result_summary}")
        else:
            logger.info(f"[MCP] [RESPONSE] Response type: {type(result).__name__}")
        
        return response
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[MCP] [ERROR] Error processing MCP request: {error_msg}", exc_info=True)
        logger.error(f"[MCP] [RESPONSE] Request failed - method={request.method}, id={request_id}, status=error, error={error_msg}")
        
        return McpResponse(
            id=request_id,
            error=McpError(
                code=-32603,
                message="Internal Error",
                data=error_msg
            )
        )


def list_tools() -> Dict[str, Any]:
    """List all available MCP tools."""
    tools = [
        {
            "name": "get_leave_balance",
            "description": "Get leave balance for an employee. Returns current year balance by default if year not specified.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "Employee ID (required)"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year for leave balance (optional, defaults to current year if not provided)"
                    }
                },
                "required": ["employee_id"]
            }
        },
        {
            "name": "submit_leave_request",
            "description": "Submit a leave request",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "Employee ID"
                    },
                    "leave_type": {
                        "type": "string",
                        "description": "Leave type (PTO, SICK, UNPAID, etc.)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for leave"
                    }
                },
                "required": ["employee_id", "leave_type", "start_date", "end_date"]
            }
        },
        {
            "name": "get_leave_history",
            "description": "Get leave request history for an employee",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "Employee ID"
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status (PENDING, APPROVED, REJECTED, etc.)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination"
                    }
                },
                "required": ["employee_id"]
            }
        },
        {
            "name": "get_pending_approvals",
            "description": "Get pending leave approvals for a manager",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "manager_id": {
                        "type": "string",
                        "description": "Manager employee ID"
                    }
                },
                "required": ["manager_id"]
            }
        },
        {
            "name": "create_hitl_request",
            "description": "Create a Human-in-the-Loop request",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "request_type": {
                        "type": "string",
                        "description": "Request type (LEAVE_EXCEPTION, POLICY_INTERPRETATION, etc.)"
                    },
                    "related_entity_type": {
                        "type": "string",
                        "description": "Related entity type (leave_request, employee, etc.)"
                    },
                    "related_entity_id": {
                        "type": "integer",
                        "description": "Related entity ID"
                    },
                    "employee_id": {
                        "type": "string",
                        "description": "Employee ID"
                    },
                    "query": {
                        "type": "string",
                        "description": "Query or request description"
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority (LOW, MEDIUM, HIGH)"
                    }
                },
                "required": ["request_type", "query"]
            }
        },
        {
            "name": "get_hitl_status",
            "description": "Get HITL request status",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hitl_request_id": {
                        "type": "integer",
                        "description": "HITL request ID"
                    }
                },
                "required": ["hitl_request_id"]
            }
        }
    ]
    
    return {"tools": tools}


def call_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Execute an MCP tool.
    
    Args:
        tool_name: Tool name
        arguments: Tool arguments
        
    Returns:
        Tool execution result
    """
    # Log tool execution start
    logger.info(f"[MCP] [TOOL_EXEC] Starting execution of tool: {tool_name}")
    logger.info(f"[MCP] [TOOL_EXEC] Tool arguments: {arguments}")
    
    # Get database session
    db = next(get_db())
    
    try:
        if tool_name == "get_leave_balance":
            service = LeaveBalanceService(db)
            employee_id = arguments.get("employee_id")
            if not employee_id:
                raise ValueError("employee_id is required")
            
            year = arguments.get("year")
            if year and isinstance(year, str):
                try:
                    year = int(year)
                except ValueError:
                    raise ValueError("year must be a valid integer")
            
            logger.info(f"[MCP] [TOOL_EXEC] Calling LeaveBalanceService.get_leave_balance(employee_id={employee_id}, year={year})")
            result = service.get_leave_balance(employee_id, year)
            # Log result details
            if isinstance(result, dict):
                balances_count = len(result.get("balances", [])) if isinstance(result, dict) else 0
                logger.info(f"[MCP] [TOOL_EXEC] get_leave_balance completed successfully for employee_id={employee_id}, year={year}, balances_count={balances_count}")
            else:
                logger.info(f"[MCP] [TOOL_EXEC] get_leave_balance completed successfully for employee_id={employee_id}, year={year}")
            return result
        
        elif tool_name == "submit_leave_request":
            service = LeaveRequestService(db)
            employee_id = arguments.get("employee_id")
            leave_type = arguments.get("leave_type")
            start_date_str = arguments.get("start_date")
            end_date_str = arguments.get("end_date")
            reason = arguments.get("reason")
            
            if not all([employee_id, leave_type, start_date_str, end_date_str]):
                raise ValueError("employee_id, leave_type, start_date, and end_date are required")
            
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            
            logger.info(f"[MCP] [TOOL_EXEC] Calling LeaveRequestService.submit_leave_request(employee_id={employee_id}, leave_type={leave_type}, start_date={start_date}, end_date={end_date})")
            result = service.submit_leave_request(employee_id, leave_type, start_date, end_date, reason)
            logger.info(f"[MCP] [TOOL_EXEC] submit_leave_request completed successfully for employee_id={employee_id}")
            return result
        
        elif tool_name == "get_leave_history":
            service = LeaveRequestService(db)
            employee_id = arguments.get("employee_id")
            if not employee_id:
                raise ValueError("employee_id is required")
            
            status = arguments.get("status")
            limit = arguments.get("limit")
            offset = arguments.get("offset")
            
            if limit and isinstance(limit, str):
                limit = int(limit)
            if offset and isinstance(offset, str):
                offset = int(offset)
            
            logger.info(f"[MCP] [TOOL_EXEC] Calling LeaveRequestService.get_leave_history(employee_id={employee_id}, status={status}, limit={limit}, offset={offset})")
            result = service.get_leave_history(employee_id, status, limit, offset)
            logger.info(f"[MCP] [TOOL_EXEC] get_leave_history completed successfully for employee_id={employee_id}, returned {len(result.get('requests', [])) if isinstance(result, dict) else 0} requests")
            return result
        
        elif tool_name == "get_pending_approvals":
            service = LeaveRequestService(db)
            manager_id = arguments.get("manager_id")
            if not manager_id:
                raise ValueError("manager_id is required")
            
            logger.info(f"[MCP] [TOOL_EXEC] Calling LeaveRequestService.get_pending_approvals(manager_id={manager_id})")
            result = service.get_pending_approvals(manager_id)
            logger.info(f"[MCP] [TOOL_EXEC] get_pending_approvals completed successfully for manager_id={manager_id}, returned {len(result.get('pending_requests', [])) if isinstance(result, dict) else 0} pending requests")
            return result
        
        elif tool_name == "create_hitl_request":
            service = HitlService(db)
            request_type = arguments.get("request_type")
            query = arguments.get("query")
            
            if not request_type or not query:
                raise ValueError("request_type and query are required")
            
            logger.info(f"[MCP] [TOOL_EXEC] Calling HitlService.create_hitl_request(request_type={request_type}, query={query[:50]}...)")
            result = service.create_hitl_request(
                request_type=request_type,
                query=query,
                related_entity_type=arguments.get("related_entity_type"),
                related_entity_id=arguments.get("related_entity_id"),
                employee_id=arguments.get("employee_id"),
                context=arguments.get("context"),
                priority=arguments.get("priority")
            )
            hitl_id = result.get("hitl_request_id") if isinstance(result, dict) else None
            logger.info(f"[MCP] [TOOL_EXEC] create_hitl_request completed successfully, hitl_request_id={hitl_id}")
            return result
        
        elif tool_name == "get_hitl_status":
            service = HitlService(db)
            hitl_request_id = arguments.get("hitl_request_id")
            if not hitl_request_id:
                raise ValueError("hitl_request_id is required")
            
            if isinstance(hitl_request_id, str):
                hitl_request_id = int(hitl_request_id)
            
            logger.info(f"[MCP] [TOOL_EXEC] Calling HitlService.get_hitl_request(hitl_request_id={hitl_request_id})")
            result = service.get_hitl_request(hitl_request_id)
            status = result.get("status") if isinstance(result, dict) else None
            logger.info(f"[MCP] [TOOL_EXEC] get_hitl_status completed successfully for hitl_request_id={hitl_request_id}, status={status}")
            return result
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    except (BusinessException, ResourceNotFoundException) as e:
        error_msg = str(e)
        logger.error(f"[MCP] [TOOL_EXEC] Business error executing tool {tool_name}: {error_msg}")
        logger.error(f"[MCP] [TOOL_RESULT] Tool '{tool_name}' failed with business error: {error_msg}")
        return {
            "error": error_msg,
            "status": "error"
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[MCP] [TOOL_EXEC] Error executing tool {tool_name}: {error_msg}", exc_info=True)
        logger.error(f"[MCP] [TOOL_RESULT] Tool '{tool_name}' failed with exception: {error_msg}")
        return {
            "error": error_msg,
            "status": "error"
        }
    finally:
        db.close()
        logger.debug(f"[MCP] [TOOL_EXEC] Database session closed for tool: {tool_name}")




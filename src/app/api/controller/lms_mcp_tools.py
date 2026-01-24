"""
MCP Tools for Leave Management System.

This module defines all MCP tools using a decorator pattern for registration.
Each tool is a standalone function with validation and proper error handling.
"""

from typing import Any, Dict, Callable, Optional
from functools import wraps
from datetime import datetime
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ValidationError

from src.app.repos.database import get_db
from src.app.services.leave_balance_service import LeaveBalanceService
from src.app.services.leave_request_service import LeaveRequestService
from src.app.services.hitl_service import HitlService
from src.app.exceptions.exceptions import BusinessException, ResourceNotFoundException
from src.app.common.config.app_logging import get_logger

logger = get_logger("lms_mcp_tools")


# ============================================================================
# Tool Registry
# ============================================================================

class MCPToolDefinition:
    """Definition of an MCP tool with metadata."""
    
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict,
        handler: Callable,
        requires_api_key: bool = True
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler
        self.requires_api_key = requires_api_key
    
    def to_dict(self) -> dict:
        """Convert to MCP tool dictionary format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


class MCPToolRegistry:
    """Registry for MCP tools."""
    
    def __init__(self):
        self._tools: Dict[str, MCPToolDefinition] = {}
        logger.info("[MCP] Tool Registry: Initialized")
    
    def register(
        self,
        name: str,
        description: str,
        input_schema: dict,
        requires_api_key: bool = True
    ):
        """
        Decorator to register an MCP tool.
        
        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for tool inputs
            requires_api_key: Whether tool requires API key (default: True)
        """
        def decorator(func: Callable) -> Callable:
            tool_def = MCPToolDefinition(
                name=name,
                description=description,
                input_schema=input_schema,
                handler=func,
                requires_api_key=requires_api_key
            )
            self._tools[name] = tool_def
            logger.info(f"[MCP] Tool Registry: Registered tool '{name}'")
            return func
        return decorator
    
    def get_tool(self, name: str) -> Optional[MCPToolDefinition]:
        """Get tool definition by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list:
        """List all registered tools in MCP format."""
        return [tool.to_dict() for tool in self._tools.values()]
    
    def execute_tool(self, name: str, arguments: Dict[str, Any], db: Session) -> Any:
        """
        Execute a tool by name.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            db: Database session
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
        """
        tool_def = self.get_tool(name)
        if not tool_def:
            raise ValueError(f"Unknown tool: {name}")
        
        logger.info(f"[MCP] Tool Registry: Executing tool '{name}'")
        return tool_def.handler(arguments, db)


# Global registry instance
tool_registry = MCPToolRegistry()


# ============================================================================
# Validation Models
# ============================================================================

class GetLeaveBalanceArgs(BaseModel):
    """Arguments for get_leave_balance tool."""
    employee_id: str = Field(..., description="Employee ID (required)")
    year: Optional[int] = Field(None, description="Year for leave balance (optional, defaults to current year)")


class SubmitLeaveRequestArgs(BaseModel):
    """Arguments for submit_leave_request tool."""
    employee_id: str = Field(..., description="Employee ID")
    leave_type: str = Field(..., description="Leave type (PTO, SICK, UNPAID, etc.)")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    reason: Optional[str] = Field(None, description="Reason for leave")


class GetLeaveHistoryArgs(BaseModel):
    """Arguments for get_leave_history tool."""
    employee_id: str = Field(..., description="Employee ID")
    status: Optional[str] = Field(None, description="Filter by status (PENDING, APPROVED, REJECTED, etc.)")
    limit: Optional[int] = Field(None, description="Maximum number of results")
    offset: Optional[int] = Field(None, description="Offset for pagination")


class GetPendingApprovalsArgs(BaseModel):
    """Arguments for get_pending_approvals tool."""
    manager_id: str = Field(..., description="Manager employee ID")


class CreateHITLRequestArgs(BaseModel):
    """Arguments for create_hitl_request tool."""
    request_type: str = Field(..., description="Request type (LEAVE_EXCEPTION, POLICY_INTERPRETATION, etc.)")
    query: str = Field(..., description="Query or request description")
    related_entity_type: Optional[str] = Field(None, description="Related entity type (leave_request, employee, etc.)")
    related_entity_id: Optional[int] = Field(None, description="Related entity ID")
    employee_id: Optional[str] = Field(None, description="Employee ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    priority: Optional[str] = Field(None, description="Priority (LOW, MEDIUM, HIGH)")


class GetHITLStatusArgs(BaseModel):
    """Arguments for get_hitl_status tool."""
    hitl_request_id: int = Field(..., description="HITL request ID")


# ============================================================================
# Tool Implementations
# ============================================================================

@tool_registry.register(
    name="get_leave_balance",
    description="Get leave balance for an employee. Returns current year balance by default if year not specified.",
    input_schema={
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
    },
    requires_api_key=True
)
def get_leave_balance_tool(args: Dict[str, Any], db: Session) -> dict:
    """
    Get leave balance tool implementation.
    
    Args:
        args: Tool arguments
        db: Database session
        
    Returns:
        Leave balance details
    """
    try:
        # Validate arguments
        validated_args = GetLeaveBalanceArgs(**args)
        
        # Execute service
        service = LeaveBalanceService(db)
        result = service.get_leave_balance(
            employee_id=validated_args.employee_id,
            year=validated_args.year
        )
        
        logger.info(
            f"[MCP] Tool: get_leave_balance completed - "
            f"employee_id={validated_args.employee_id}, "
            f"year={validated_args.year}, "
            f"balances_count={len(result.get('balances', []))}"
        )
        
        return result
        
    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: get_leave_balance validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: get_leave_balance business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: get_leave_balance execution error - {str(e)}")
        raise


@tool_registry.register(
    name="submit_leave_request",
    description="Submit a leave request",
    input_schema={
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
    },
    requires_api_key=True
)
def submit_leave_request_tool(args: Dict[str, Any], db: Session) -> dict:
    """
    Submit leave request tool implementation.
    
    Args:
        args: Tool arguments
        db: Database session
        
    Returns:
        Leave request details
    """
    try:
        # Validate arguments
        validated_args = SubmitLeaveRequestArgs(**args)
        
        # Parse dates
        start_date = datetime.strptime(validated_args.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(validated_args.end_date, "%Y-%m-%d").date()
        
        # Execute service
        service = LeaveRequestService(db)
        result = service.submit_leave_request(
            employee_id=validated_args.employee_id,
            leave_type=validated_args.leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=validated_args.reason
        )
        
        logger.info(
            f"[MCP] Tool: submit_leave_request completed - "
            f"employee_id={validated_args.employee_id}, "
            f"leave_type={validated_args.leave_type}, "
            f"request_id={result.get('requestId')}"
        )
        
        return result
        
    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: submit_leave_request validation error - {error_msg}")
        raise ValueError(error_msg)
    except ValueError as e:
        # Date parsing errors
        logger.error(f"[MCP] Tool: submit_leave_request date error - {str(e)}")
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD format. Error: {str(e)}")
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: submit_leave_request business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: submit_leave_request execution error - {str(e)}")
        raise


@tool_registry.register(
    name="get_leave_history",
    description="Get leave request history for an employee",
    input_schema={
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
    },
    requires_api_key=True
)
def get_leave_history_tool(args: Dict[str, Any], db: Session) -> dict:
    """
    Get leave history tool implementation.
    
    Args:
        args: Tool arguments
        db: Database session
        
    Returns:
        Leave history details
    """
    try:
        # Validate arguments
        validated_args = GetLeaveHistoryArgs(**args)
        
        # Execute service
        service = LeaveRequestService(db)
        result = service.get_leave_history(
            employee_id=validated_args.employee_id,
            status=validated_args.status,
            limit=validated_args.limit,
            offset=validated_args.offset
        )
        
        requests_count = len(result.get('requests', [])) if isinstance(result, dict) else 0
        logger.info(
            f"[MCP] Tool: get_leave_history completed - "
            f"employee_id={validated_args.employee_id}, "
            f"requests_count={requests_count}"
        )
        
        return result
        
    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: get_leave_history validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: get_leave_history business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: get_leave_history execution error - {str(e)}")
        raise


@tool_registry.register(
    name="get_pending_approvals",
    description="Get pending leave approvals for a manager",
    input_schema={
        "type": "object",
        "properties": {
            "manager_id": {
                "type": "string",
                "description": "Manager employee ID"
            }
        },
        "required": ["manager_id"]
    },
    requires_api_key=True
)
def get_pending_approvals_tool(args: Dict[str, Any], db: Session) -> dict:
    """
    Get pending approvals tool implementation.
    
    Args:
        args: Tool arguments
        db: Database session
        
    Returns:
        Pending approvals details
    """
    try:
        # Validate arguments
        validated_args = GetPendingApprovalsArgs(**args)
        
        # Execute service
        service = LeaveRequestService(db)
        result = service.get_pending_approvals(manager_id=validated_args.manager_id)
        
        pending_count = len(result.get('pending_requests', [])) if isinstance(result, dict) else 0
        logger.info(
            f"[MCP] Tool: get_pending_approvals completed - "
            f"manager_id={validated_args.manager_id}, "
            f"pending_count={pending_count}"
        )
        
        return result
        
    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: get_pending_approvals validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: get_pending_approvals business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: get_pending_approvals execution error - {str(e)}")
        raise


@tool_registry.register(
    name="create_hitl_request",
    description="Create a Human-in-the-Loop request",
    input_schema={
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
    },
    requires_api_key=True
)
def create_hitl_request_tool(args: Dict[str, Any], db: Session) -> dict:
    """
    Create HITL request tool implementation.
    
    Args:
        args: Tool arguments
        db: Database session
        
    Returns:
        HITL request details
    """
    try:
        # Validate arguments
        validated_args = CreateHITLRequestArgs(**args)
        
        # Execute service
        service = HitlService(db)
        result = service.create_hitl_request(
            request_type=validated_args.request_type,
            query=validated_args.query,
            related_entity_type=validated_args.related_entity_type,
            related_entity_id=validated_args.related_entity_id,
            employee_id=validated_args.employee_id,
            context=validated_args.context,
            priority=validated_args.priority
        )
        
        hitl_id = result.get("hitlRequestId") if isinstance(result, dict) else None
        logger.info(
            f"[MCP] Tool: create_hitl_request completed - "
            f"hitl_request_id={hitl_id}, "
            f"request_type={validated_args.request_type}"
        )
        
        return result
        
    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: create_hitl_request validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: create_hitl_request business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: create_hitl_request execution error - {str(e)}")
        raise


@tool_registry.register(
    name="get_hitl_status",
    description="Get HITL request status",
    input_schema={
        "type": "object",
        "properties": {
            "hitl_request_id": {
                "type": "integer",
                "description": "HITL request ID"
            }
        },
        "required": ["hitl_request_id"]
    },
    requires_api_key=True
)
def get_hitl_status_tool(args: Dict[str, Any], db: Session) -> dict:
    """
    Get HITL status tool implementation.
    
    Args:
        args: Tool arguments
        db: Database session
        
    Returns:
        HITL request status details
    """
    try:
        # Handle string to int conversion for hitl_request_id
        hitl_request_id = args.get("hitl_request_id")
        if isinstance(hitl_request_id, str):
            try:
                hitl_request_id = int(hitl_request_id)
            except ValueError:
                raise ValueError("hitl_request_id must be a valid integer")
        
        # Validate arguments
        validated_args = GetHITLStatusArgs(hitl_request_id=hitl_request_id)
        
        # Execute service
        service = HitlService(db)
        result = service.get_hitl_request(validated_args.hitl_request_id)
        
        status = result.get("status") if isinstance(result, dict) else None
        logger.info(
            f"[MCP] Tool: get_hitl_status completed - "
            f"hitl_request_id={validated_args.hitl_request_id}, "
            f"status={status}"
        )
        
        return result
        
    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: get_hitl_status validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: get_hitl_status business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: get_hitl_status execution error - {str(e)}")
        raise

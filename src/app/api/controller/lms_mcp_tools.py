"""
MCP Tools for Leave Management System.

This module defines all MCP tools using FastMCP decorator pattern.
Each tool is a standalone function with validation and proper error handling.
"""

from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import ValidationError

from mcp.server.fastmcp import FastMCP

from src.app.repos.database import get_db
from src.app.services.leave_balance_service import LeaveBalanceService
from src.app.services.leave_request_service import LeaveRequestService
from src.app.services.hitl_service import HitlService
from src.app.exceptions.exceptions import BusinessException, ResourceNotFoundException
from src.app.common.config.app_logging import get_logger

# Import validation models from existing files (for validation)
from src.app.models.get_leave_balance_args import GetLeaveBalanceArgs
from src.app.models.submit_leave_balance_args import SubmitLeaveRequestArgs
from src.app.models.get_leave_history_args import GetLeaveHistoryArgs
from src.app.models.get_pending_approvals_args import GetPendingApprovalsArgs
from src.app.models.create_hitl_requests_args import CreateHITLRequestArgs
from src.app.models.get_hitl_status_args import GetHITLStatusArgs

logger = get_logger("lms_mcp_tools")

# Initialize FastMCP server with stateless HTTP and JSON responses
# Stateless mode: No session ID required, creates new transport per request
# JSON responses: Returns JSON instead of SSE streams (simpler for HTTP clients)
mcp = FastMCP("lms")
mcp.settings.stateless_http = True
mcp.settings.json_response = True


# ============================================================================
# Tool Implementations using FastMCP
# ============================================================================

@mcp.tool()
def get_leave_balance(employee_id: str, year: Optional[int] = None) -> dict:
    """
    Get leave balance for an employee. Returns current year balance by default if year not specified.
    
    Args:
        employee_id: Employee ID (required)
        year: Year for leave balance (optional, defaults to current year)
        
    Returns:
        Leave balance details
    """
    # Log raw payload for troubleshooting
    logger.info(f"[MCP] Tool: get_leave_balance CALLED - employee_id={employee_id}, year={year}")
    
    # Get database session
    db = next(get_db())
    try:
        # Validate arguments using Pydantic model
        validated_args = GetLeaveBalanceArgs(employee_id=employee_id, year=year)
        
        # Execute service
        service = LeaveBalanceService(db)
        result = service.get_leave_balance(
            employee_id=validated_args.employee_id,
            year=validated_args.year
        )
        
        logger.info(
            f"[MCP] Tool: get_leave_balance completed - "
            f"employee_id={validated_args.employee_id}, "
            f"year_input={validated_args.year}, "
            f"year_resolved={result.get('year')}, "
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
    finally:
        db.close()


@mcp.tool()
def submit_leave_request(
    employee_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: Optional[str] = None
) -> dict:
    """
    Submit a leave request.
    
    Args:
        employee_id: Employee ID
        leave_type: Leave type (PTO, SICK, UNPAID, etc.)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        reason: Reason for leave (optional)
        
    Returns:
        Leave request details
    """
    # Log raw payload for troubleshooting
    logger.info(f"[MCP] Tool: submit_leave_request CALLED - employee_id={employee_id}, leave_type={leave_type}, start_date={start_date}, end_date={end_date}, reason={reason}")
    
    # Get database session
    db = next(get_db())
    try:
        # Validate arguments
        validated_args = SubmitLeaveRequestArgs(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )
        
        # Parse dates
        parsed_start_date = datetime.strptime(validated_args.start_date, "%Y-%m-%d").date()
        parsed_end_date = datetime.strptime(validated_args.end_date, "%Y-%m-%d").date()
        
        # Execute service
        service = LeaveRequestService(db)
        result = service.submit_leave_request(
            employee_id=validated_args.employee_id,
            leave_type=validated_args.leave_type,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
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
    finally:
        db.close()


@mcp.tool()
def get_leave_history(
    employee_id: str,
    year: Optional[int] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> dict:
    """
    Get leave request history for an employee.
    
    Args:
        employee_id: Employee ID
        year: Year for which to retrieve leave history (optional, returns all years if not specified)
        status: Filter by status (PENDING, APPROVED, REJECTED, PENDING_HITL, or 'all' for no filter)
        limit: Maximum number of results (optional)
        offset: Offset for pagination (optional)
        
    Returns:
        Leave history details
    """
    # Log raw payload for troubleshooting
    logger.info(f"[MCP] Tool: get_leave_history CALLED - employee_id={employee_id}, year={year}, status={status}, limit={limit}, offset={offset}")
    
    # Get database session
    db = next(get_db())
    try:
        # Validate arguments
        validated_args = GetLeaveHistoryArgs(
            employee_id=employee_id,
            year=year,
            status=status,
            limit=limit,
            offset=offset
        )
        
        # Execute service
        service = LeaveRequestService(db)
        result = service.get_leave_history(
            employee_id=validated_args.employee_id,
            year=validated_args.year,
            status=validated_args.status,
            limit=validated_args.limit,
            offset=validated_args.offset
        )
        
        requests_count = len(result.get('requests', [])) if isinstance(result, dict) else 0
        logger.info(
            f"[MCP] Tool: get_leave_history completed - "
            f"employee_id={validated_args.employee_id}, "
            f"year={validated_args.year}, "
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
    finally:
        db.close()


@mcp.tool()
def get_pending_approvals(manager_id: str) -> dict:
    """
    Get pending leave approvals for a manager.
    
    Args:
        manager_id: Manager employee ID
        
    Returns:
        Pending approvals details
    """
    # Log raw payload for troubleshooting
    logger.info(f"[MCP] Tool: get_pending_approvals CALLED - manager_id={manager_id}")
    
    # Get database session
    db = next(get_db())
    try:
        # Validate arguments
        validated_args = GetPendingApprovalsArgs(manager_id=manager_id)
        
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
    finally:
        db.close()


@mcp.tool()
def create_hitl_request(
    request_type: str,
    query: str,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
    employee_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    priority: Optional[str] = None
) -> dict:
    """
    Create a Human-in-the-Loop request.
    
    Args:
        request_type: Request type (LEAVE_EXCEPTION, POLICY_INTERPRETATION, etc.)
        query: Query or request description
        related_entity_type: Related entity type (leave_request, employee, etc.) - optional
        related_entity_id: Related entity ID - optional
        employee_id: Employee ID - optional
        context: Additional context - optional
        priority: Priority (LOW, MEDIUM, HIGH) - optional
        
    Returns:
        HITL request details
    """
    # Log raw payload for troubleshooting
    logger.info(f"[MCP] Tool: create_hitl_request CALLED - request_type={request_type}, query={query}, related_entity_type={related_entity_type}, related_entity_id={related_entity_id}, employee_id={employee_id}, priority={priority}")
    
    # Get database session
    db = next(get_db())
    try:
        # Validate arguments
        validated_args = CreateHITLRequestArgs(
            request_type=request_type,
            query=query,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            employee_id=employee_id,
            context=context,
            priority=priority
        )
        
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
    finally:
        db.close()


@mcp.tool()
def get_hitl_status(hitl_request_id: int) -> dict:
    """
    Get HITL request status.
    
    Args:
        hitl_request_id: HITL request ID
        
    Returns:
        HITL request status details
    """
    # Log raw payload for troubleshooting
    logger.info(f"[MCP] Tool: get_hitl_status CALLED - hitl_request_id={hitl_request_id}")
    
    # Get database session
    db = next(get_db())
    try:
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
    finally:
        db.close()

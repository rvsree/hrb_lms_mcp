"""
MCP Tools for Leave Management System.

This module defines all MCP tools using FastMCP decorator pattern.
Each tool is a standalone function with validation and proper error handling.

Tools are registered with the FastMCP server instance imported from mcp_server.
This follows modular architecture: server configuration is separate from tool definitions.
"""

from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import ValidationError

# Import the FastMCP server instance from mcp_server module
# This ensures a single source of truth for server configuration
from src.app.api.mcp_server import mcp

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
from src.app.models.resolve_hitl_request_args import ResolveHITLRequestArgs
from src.app.models.submit_unpaid_leave_request_args import SubmitUnpaidLeaveRequestArgs
from src.app.models.list_hitl_requests_args import ListHITLRequestsArgs
from src.app.models.register_leave_document_args import RegisterLeaveDocumentArgs
from src.app.models.list_leave_documents_args import ListLeaveDocumentsArgs
from src.app.models.list_my_leave_requests_args import ListMyLeaveRequestsArgs
from src.app.models.admin_delete_hitl_request_args import AdminDeleteHitlRequestArgs
from src.app.models.list_all_leave_requests_args import ListAllLeaveRequestsArgs
from src.app.models.set_review_brief_args import SetReviewBriefArgs
from src.app.models.record_produced_artifact_args import RecordProducedArtifactArgs

logger = get_logger("lms_mcp_tools")


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
        leave_type: Leave type code. MUST be one of: "PTO" (Paid Time Off - for vacation, personal time), 
                    "SICK" (Sick Leave - for illness, medical appointments, surgery recovery).
                    Do NOT use "MEDICAL", "VACATION", or other types - they will fail.
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


@mcp.tool()
def resolve_hitl_request(
    hitl_request_id: int,
    decision: str,
    response_text: str,
    resolved_by: Optional[str] = None,
    resolved_by_employee_id: Optional[str] = None
) -> dict:
    """
    Resolve a HITL request with a human decision - approve or reject.

    This is the missing half of the HITL loop: create_hitl_request and
    get_hitl_status already existed, but nothing could ever move a request
    out of PENDING. When the request is tied to a leave request, that leave
    request's own status is updated in the same transaction.

    Args:
        hitl_request_id: HITL request ID to resolve
        decision: APPROVED or REJECTED
        response_text: The specialist's explanation/notes for this decision
        resolved_by: Identifier of the specialist who resolved this, e.g. an email

    Returns:
        Resolved HITL request details
    """
    # Log raw payload for troubleshooting
    logger.info(f"[MCP] Tool: resolve_hitl_request CALLED - hitl_request_id={hitl_request_id}, decision={decision}, resolved_by={resolved_by}")

    # Get database session
    db = next(get_db())
    try:
        # Validate arguments
        validated_args = ResolveHITLRequestArgs(
            hitl_request_id=hitl_request_id,
            decision=decision,
            response_text=response_text,
            resolved_by=resolved_by,
            resolved_by_employee_id=resolved_by_employee_id
        )

        # Execute service
        service = HitlService(db)
        result = service.resolve_hitl_request(
            hitl_request_id=validated_args.hitl_request_id,
            decision=validated_args.decision,
            response_text=validated_args.response_text,
            resolved_by=validated_args.resolved_by,
            resolved_by_employee_id=validated_args.resolved_by_employee_id
        )

        logger.info(
            f"[MCP] Tool: resolve_hitl_request completed - "
            f"hitl_request_id={validated_args.hitl_request_id}, "
            f"decision={result.get('decision')}, "
            f"related_leave_request_updated={result.get('relatedLeaveRequestUpdated')}"
        )

        return result

    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: resolve_hitl_request validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: resolve_hitl_request business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: resolve_hitl_request execution error - {str(e)}")
        raise
    finally:
        db.close()


@mcp.tool()
def submit_unpaid_leave_request(
    employee_id: str,
    start_date: str,
    end_date: str,
    purpose: str,
    is_repeat_within_12_months: bool,
    leave_type_code: str = "UNPAID",
    document_reference: Optional[str] = None
) -> dict:
    """
    Submit an unpaid leave request. Always routed to HR specialist review
    via a HITL request, regardless of balance - unpaid leave has none,
    unlike submit_leave_request's balance-exception path.

    Args:
        employee_id: Employee ID
        start_date: Leave start date (YYYY-MM-DD)
        end_date: Leave end date (YYYY-MM-DD)
        purpose: Reason/purpose for the unpaid leave request
        is_repeat_within_12_months: Whether the employee has taken unpaid leave
            in the last 12 months - the caller must check this itself via
            get_leave_history before calling this tool, not assume it.
        document_reference: S3 key or URI of a supporting document, if one was uploaded

    Returns:
        Submitted leave request details, including the HITL request it created
    """
    # Log raw payload for troubleshooting
    logger.info(f"[MCP] Tool: submit_unpaid_leave_request CALLED - employee_id={employee_id}, start_date={start_date}, end_date={end_date}, is_repeat_within_12_months={is_repeat_within_12_months}")

    # Get database session
    db = next(get_db())
    try:
        # Validate arguments
        validated_args = SubmitUnpaidLeaveRequestArgs(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            purpose=purpose,
            is_repeat_within_12_months=is_repeat_within_12_months,
            leave_type_code=leave_type_code,
            document_reference=document_reference
        )

        # Parse dates
        parsed_start_date = datetime.strptime(validated_args.start_date, "%Y-%m-%d").date()
        parsed_end_date = datetime.strptime(validated_args.end_date, "%Y-%m-%d").date()

        # Execute service
        service = LeaveRequestService(db)
        result = service.submit_unpaid_leave_request(
            employee_id=validated_args.employee_id,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            purpose=validated_args.purpose,
            is_repeat_within_12_months=validated_args.is_repeat_within_12_months,
            leave_type_code=validated_args.leave_type_code,
            document_reference=validated_args.document_reference
        )

        logger.info(
            f"[MCP] Tool: submit_unpaid_leave_request completed - "
            f"employee_id={validated_args.employee_id}, "
            f"request_id={result.get('requestId')}, "
            f"hitl_request_id={result.get('hitlRequestId')}"
        )

        return result

    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: submit_unpaid_leave_request validation error - {error_msg}")
        raise ValueError(error_msg)
    except ValueError as e:
        # Date parsing errors
        logger.error(f"[MCP] Tool: submit_unpaid_leave_request date error - {str(e)}")
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD format. Error: {str(e)}")
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: submit_unpaid_leave_request business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: submit_unpaid_leave_request execution error - {str(e)}")
        raise
    finally:
        db.close()


@mcp.tool()
def list_hitl_requests(
    status: Optional[str] = None,
    request_type: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> dict:
    """
    List HITL requests, optionally filtered by status and/or request type.
    Needed for a specialist review queue - create_hitl_request/get_hitl_status
    only ever operated on one known ID, nothing could list what's pending.

    Args:
        status: Filter by status (PENDING, IN_PROGRESS, COMPLETED, CANCELLED, or 'all'). Defaults to PENDING.
        request_type: Filter by request type, e.g. UNPAID_LEAVE_REQUEST - optional
        limit: Maximum number of results (optional)
        offset: Offset for pagination (optional)

    Returns:
        Matching HITL requests
    """
    # Log raw payload for troubleshooting
    logger.info(f"[MCP] Tool: list_hitl_requests CALLED - status={status}, request_type={request_type}, limit={limit}, offset={offset}")

    # Get database session
    db = next(get_db())
    try:
        # Validate arguments
        validated_args = ListHITLRequestsArgs(
            status=status,
            request_type=request_type,
            limit=limit,
            offset=offset
        )

        # Execute service
        service = HitlService(db)
        result = service.list_hitl_requests(
            status=validated_args.status,
            request_type=validated_args.request_type,
            limit=validated_args.limit,
            offset=validated_args.offset
        )

        requests_count = len(result.get('requests', [])) if isinstance(result, dict) else 0
        logger.info(
            f"[MCP] Tool: list_hitl_requests completed - "
            f"status={status}, requests_count={requests_count}"
        )

        return result

    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: list_hitl_requests validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: list_hitl_requests business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: list_hitl_requests execution error - {str(e)}")
        raise
    finally:
        db.close()


@mcp.tool()
def register_leave_document(
    employee_id: str,
    s3_key: str,
    original_filename: str,
    content_type: Optional[str] = None
) -> dict:
    """
    Phase 165 - registers an uploaded leave document's manifest row at
    upload time, before the leave request it belongs to exists yet. Closes
    a real orphan-upload gap: without this, a failed submit after a
    successful S3 upload left nothing in any database pointing at the
    uploaded file. submit_unpaid_leave_request links this row to the real
    leave request once it's created, by matching document_reference (the
    same s3_key) back to this row.

    Args:
        employee_id: Employee ID (validated here only to reject an unknown caller early)
        s3_key: The S3 object key the file was uploaded to
        original_filename: The file's original name, for display
        content_type: The file's MIME type, if known

    Returns:
        The new manifest row's id and s3_key
    """
    logger.info(f"[MCP] Tool: register_leave_document CALLED - employee_id={employee_id}, s3_key={s3_key}")

    db = next(get_db())
    try:
        validated_args = RegisterLeaveDocumentArgs(
            employee_id=employee_id,
            s3_key=s3_key,
            original_filename=original_filename,
            content_type=content_type
        )

        service = LeaveRequestService(db)
        result = service.register_leave_document(
            employee_id=validated_args.employee_id,
            s3_key=validated_args.s3_key,
            original_filename=validated_args.original_filename,
            content_type=validated_args.content_type
        )

        logger.info(f"[MCP] Tool: register_leave_document completed - document_id={result.get('documentId')}")

        return result

    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: register_leave_document validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: register_leave_document business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: register_leave_document execution error - {str(e)}")
        raise
    finally:
        db.close()


@mcp.tool()
def list_leave_documents(leave_request_id: int) -> dict:
    """
    Phase 165 - the manifest rows for one leave request's uploaded
    document(s). Used by both the HR specialist review queue and the
    employee's own "My Requests" view to know what to request a download
    URL for.

    Args:
        leave_request_id: The leave request whose uploaded documents to list

    Returns:
        The matching document manifest rows
    """
    logger.info(f"[MCP] Tool: list_leave_documents CALLED - leave_request_id={leave_request_id}")

    db = next(get_db())
    try:
        validated_args = ListLeaveDocumentsArgs(leave_request_id=leave_request_id)

        service = LeaveRequestService(db)
        result = service.list_leave_documents(leave_request_id=validated_args.leave_request_id)

        logger.info(
            f"[MCP] Tool: list_leave_documents completed - "
            f"leave_request_id={leave_request_id}, count={len(result.get('documents', []))}"
        )

        return result

    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: list_leave_documents validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: list_leave_documents business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: list_leave_documents execution error - {str(e)}")
        raise
    finally:
        db.close()


@mcp.tool()
def list_my_leave_requests(
    employee_id: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> dict:
    """
    Phase 165 - the employee's own "My Requests" view: every specialist-
    reviewed leave request they've submitted (UNPAID/CRITICAL_CAREGIVER/
    STD/LTD), joined to its review's current status/comments/timestamps.
    Scoped to the caller's own employee_id only.

    Args:
        employee_id: Employee ID - returns only their own requests
        limit: Maximum number of results (optional)
        offset: Offset for pagination (optional)

    Returns:
        The matching leave requests with their review status
    """
    logger.info(f"[MCP] Tool: list_my_leave_requests CALLED - employee_id={employee_id}")

    db = next(get_db())
    try:
        validated_args = ListMyLeaveRequestsArgs(employee_id=employee_id, limit=limit, offset=offset)

        service = LeaveRequestService(db)
        result = service.list_my_leave_requests(
            employee_id=validated_args.employee_id,
            limit=validated_args.limit,
            offset=validated_args.offset
        )

        logger.info(
            f"[MCP] Tool: list_my_leave_requests completed - "
            f"employee_id={employee_id}, total={result.get('total')}"
        )

        return result

    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: list_my_leave_requests validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: list_my_leave_requests business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: list_my_leave_requests execution error - {str(e)}")
        raise
    finally:
        db.close()


@mcp.tool()
def admin_delete_hitl_request(hitl_request_id: int) -> dict:
    """
    Phase 168 - admin-only hard delete of a HITL request and everything
    that hangs off it (its SpecialistLeaveReview, its related
    LeaveRequest, and its UnpaidLeaveDocument manifest rows). For a
    "clean up test data" admin tool, not a normal application flow - this
    is the only delete-capable tool in this entire server.

    Args:
        hitl_request_id: HITL request ID to delete, with everything that hangs off it

    Returns:
        What was deleted - counts and the S3 keys the caller (which owns
        the real S3 client) still needs to delete the actual objects for
    """
    logger.info(f"[MCP] Tool: admin_delete_hitl_request CALLED - hitl_request_id={hitl_request_id}")

    db = next(get_db())
    try:
        validated_args = AdminDeleteHitlRequestArgs(hitl_request_id=hitl_request_id)

        service = HitlService(db)
        result = service.admin_delete_hitl_request(hitl_request_id=validated_args.hitl_request_id)

        logger.info(
            f"[MCP] Tool: admin_delete_hitl_request completed - "
            f"hitl_request_id={hitl_request_id}, deleted_leave_request={result.get('deletedLeaveRequest')}, "
            f"deleted_documents={len(result.get('deletedDocumentS3Keys', []))}"
        )

        return result

    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: admin_delete_hitl_request validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: admin_delete_hitl_request business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: admin_delete_hitl_request execution error - {str(e)}")
        raise
    finally:
        db.close()


@mcp.tool()
def set_review_brief(hitl_request_id: int, review_brief: str) -> dict:
    """
    Phase 172 - stores the specialist-facing LLM-generated summary onto
    the review row, right after it's generated and before the calling
    agent graph pauses waiting on the specialist.

    Args:
        hitl_request_id: HITL request ID this review brief belongs to
        review_brief: The generated plain-English summary text

    Returns:
        Confirmation that the write succeeded
    """
    logger.info(f"[MCP] Tool: set_review_brief CALLED - hitl_request_id={hitl_request_id}")

    db = next(get_db())
    try:
        validated_args = SetReviewBriefArgs(hitl_request_id=hitl_request_id, review_brief=review_brief)

        service = LeaveRequestService(db)
        result = service.set_review_brief(
            hitl_request_id=validated_args.hitl_request_id, review_brief=validated_args.review_brief
        )

        logger.info(f"[MCP] Tool: set_review_brief completed - hitl_request_id={hitl_request_id}")
        return result

    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: set_review_brief validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: set_review_brief business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: set_review_brief execution error - {str(e)}")
        raise
    finally:
        db.close()


@mcp.tool()
def record_produced_artifact(hitl_request_id: int, artifact: Dict[str, Any]) -> dict:
    """
    Phase 172 - appends one Artifact-shaped record (e.g. the decision
    email) to the review row. Called by hrb_chatbot_v2 right after it
    actually sends that email - this repo has no email client of its own,
    so it can't record this at resolve_hitl_request() time.

    Args:
        hitl_request_id: HITL request ID this artifact belongs to
        artifact: Plain dict describing what was produced, e.g.
            {"type": "email", "recipient": "...", "sent": true, "sent_at": "..."}

    Returns:
        Confirmation that the write succeeded
    """
    logger.info(f"[MCP] Tool: record_produced_artifact CALLED - hitl_request_id={hitl_request_id}")

    db = next(get_db())
    try:
        validated_args = RecordProducedArtifactArgs(hitl_request_id=hitl_request_id, artifact=artifact)

        service = HitlService(db)
        result = service.record_produced_artifact(
            hitl_request_id=validated_args.hitl_request_id, artifact=validated_args.artifact
        )

        logger.info(f"[MCP] Tool: record_produced_artifact completed - hitl_request_id={hitl_request_id}")
        return result

    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: record_produced_artifact validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: record_produced_artifact business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: record_produced_artifact execution error - {str(e)}")
        raise
    finally:
        db.close()


@mcp.tool()
def list_all_leave_requests(
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> dict:
    """
    Phase 168 (round 2) - the HR specialist grid: every specialist-
    reviewed leave request across every employee, with full
    status/decision/comments/timestamps - not just PENDING ones
    (list_hitl_requests, used by /pending, only ever shows those).

    Args:
        status: Filter by review status (PENDING, IN_PROGRESS, COMPLETED, CANCELLED, or 'all'/None for every status)
        limit: Maximum number of results (optional)
        offset: Offset for pagination (optional)

    Returns:
        Every matching leave request, newest-submitted-first
    """
    logger.info(f"[MCP] Tool: list_all_leave_requests CALLED - status={status}")

    db = next(get_db())
    try:
        validated_args = ListAllLeaveRequestsArgs(status=status, limit=limit, offset=offset)

        service = LeaveRequestService(db)
        result = service.list_all_leave_requests(
            status=validated_args.status,
            limit=validated_args.limit,
            offset=validated_args.offset
        )

        logger.info(f"[MCP] Tool: list_all_leave_requests completed - total={result.get('total')}")

        return result

    except ValidationError as e:
        error_msg = f"Invalid arguments: {e.errors()}"
        logger.error(f"[MCP] Tool: list_all_leave_requests validation error - {error_msg}")
        raise ValueError(error_msg)
    except (BusinessException, ResourceNotFoundException) as e:
        logger.error(f"[MCP] Tool: list_all_leave_requests business error - {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"[MCP] Tool: list_all_leave_requests execution error - {str(e)}")
        raise
    finally:
        db.close()

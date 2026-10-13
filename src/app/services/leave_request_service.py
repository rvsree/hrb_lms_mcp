"""Leave request service."""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, extract
from datetime import datetime, date
from decimal import Decimal
from src.app.models.models import (
    Employee, LeaveRequest, LeaveType, LeaveBalance,
    LeaveRequestStatus, UnpaidLeaveDocument, SpecialistLeaveReview,
    HitlRequestStatus
)
from src.app.exceptions.exceptions import ResourceNotFoundException, BusinessException


class LeaveRequestService:
    """Service for managing leave requests."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def submit_leave_request(
        self,
        employee_id: str,
        leave_type: str,
        start_date: date,
        end_date: date,
        reason: Optional[str] = None
    ) -> dict:
        """
        Submit a leave request.
        
        Args:
            employee_id: Employee ID
            leave_type: Leave type code
            start_date: Start date
            end_date: End date
            reason: Reason for leave
            
        Returns:
            Dictionary with leave request details
        """
        # Validate dates
        if end_date < start_date:
            raise BusinessException("INVALID_DATES", "End date must be after or equal to start date")
        
        # Get employee
        employee = self.db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise ResourceNotFoundException(f"Employee not found with ID: {employee_id}")
        
        # Get leave type
        leave_type_obj = self.db.query(LeaveType).filter(LeaveType.code == leave_type).first()
        if not leave_type_obj:
            raise ResourceNotFoundException(f"Leave type not found: {leave_type}")
        
        # Calculate days (inclusive of start and end date)
        days_between = (end_date - start_date).days + 1
        days = Decimal(str(days_between))
        
        # Check leave balance if it's a paid leave type
        hitl_required = False
        hitl_request_id = None
        hitl_reason = None
        status = LeaveRequestStatus.PENDING
        
        if leave_type_obj.requires_approval and leave_type != "UNPAID":
            # Use the year from the start_date of the leave request, not current year
            # This handles cases where leave is requested for a different year
            leave_year = start_date.year
            balance = self.db.query(LeaveBalance).join(LeaveType).filter(
                and_(
                    LeaveBalance.employee_id == employee.id,
                    LeaveType.code == leave_type,
                    LeaveBalance.year == leave_year
                )
            ).first()
            
            if not balance:
                raise BusinessException(
                    "BALANCE_NOT_FOUND",
                    f"Leave balance not found for employee: {employee_id}"
                )
            
            if balance.available < days:
                # Insufficient balance - requires HITL
                hitl_required = True
                status = LeaveRequestStatus.PENDING_HITL
                hitl_reason = (
                    f"Request exceeds available balance. "
                    f"Available: {balance.available} days, "
                    f"Requested: {days} days. Requires HR approval for exception."
                )
        
        # Determine approver (manager)
        approver = employee.manager
        
        # Create leave request
        leave_request = LeaveRequest(
            employee_id=employee.id,
            leave_type_id=leave_type_obj.id,
            start_date=start_date,
            end_date=end_date,
            days=days,
            reason=reason,
            status=status,
            approver_id=approver.id if approver else None
        )
        
        self.db.add(leave_request)
        self.db.flush()  # Get the ID
        
        # Create HITL request if needed
        if hitl_required:
            from src.app.services.hitl_service import HitlService
            hitl_service = HitlService(self.db)
            hitl_request = hitl_service.create_hitl_request_for_leave_exception(
                employee, leave_type_obj, days, balance.available, leave_request.id
            )
            hitl_request_id = hitl_request["hitlRequestId"]
        
        self.db.commit()
        
        return {
            "requestId": leave_request.id,
            "employeeId": employee_id,
            "leaveType": leave_type,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "days": float(days),
            "status": status.value,
            "requiresApproval": leave_type_obj.requires_approval,
            "approverId": approver.employee_id if approver else None,
            "hitlRequired": hitl_required,
            "hitlRequestId": hitl_request_id,
            "hitlReason": hitl_reason,
            "createdAt": leave_request.created_at.isoformat() if leave_request.created_at else None
        }

    def submit_unpaid_leave_request(
        self,
        employee_id: str,
        start_date: date,
        end_date: date,
        purpose: str,
        is_repeat_within_12_months: bool,
        leave_type_code: str = "UNPAID",
        document_reference: Optional[str] = None
    ) -> dict:
        """
        Submit a specialist-reviewed leave request - always routed to HR
        specialist review via a HITL request, regardless of balance (these
        leave types have none, unlike submit_leave_request()'s balance-
        exception path). Despite the name (kept for backward compatibility -
        this is the same MCP tool Phase 162 already shipped), Phase 165
        expanded this past UNPAID-only: leave_type_code selects among
        UNPAID/CRITICAL_CAREGIVER/STD/LTD, all requires_specialist_review=True.

        is_repeat_within_12_months is computed by the caller (the calling
        agent checks get_leave_history itself, same tool this service
        already exposes) and carried through as context for the specialist
        to weigh - not re-derived here, so there's one source of truth for
        "what the specialist was actually told," not a second recomputation
        that could silently disagree with it. Phase 165: the caller scopes
        this check to the same leave_type_code only (a 2nd STD request
        within 12 months flags; an unrelated CCG request doesn't) - a real
        HR-policy distinction, not a technical default.

        Args:
            employee_id: Employee ID
            start_date: Leave start date
            end_date: Leave end date
            purpose: Reason/purpose for the request
            is_repeat_within_12_months: Whether the employee has taken this same leave type in the last 12 months
            leave_type_code: UNPAID, CRITICAL_CAREGIVER, STD, or LTD
            document_reference: S3 key of a supporting document, if one was uploaded (already registered via register_leave_document)

        Returns:
            Dictionary with the submitted request details
        """
        if end_date < start_date:
            raise BusinessException("INVALID_DATES", "End date must be after or equal to start date")

        employee = self.db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise ResourceNotFoundException(f"Employee not found with ID: {employee_id}")

        leave_type_obj = self.db.query(LeaveType).filter(LeaveType.code == leave_type_code).first()
        if not leave_type_obj:
            raise ResourceNotFoundException(f"Leave type not found: {leave_type_code}")

        days_between = (end_date - start_date).days + 1
        days = Decimal(str(days_between))

        approver = employee.manager

        leave_request = LeaveRequest(
            employee_id=employee.id,
            leave_type_id=leave_type_obj.id,
            start_date=start_date,
            end_date=end_date,
            days=days,
            reason=purpose,
            status=LeaveRequestStatus.PENDING_HITL,
            approver_id=approver.id if approver else None
        )
        self.db.add(leave_request)
        self.db.flush()  # Get the ID before the HITL request/document link reference it

        from src.app.services.hitl_service import HitlService
        hitl_service = HitlService(self.db)

        repeat_note = f"REPEAT REQUEST - taken {leave_type_obj.name} within the last 12 months. " if is_repeat_within_12_months else ""
        query = (
            f"Employee {employee.name} requests {days} days of {leave_type_obj.name} "
            f"({start_date.isoformat()} to {end_date.isoformat()}). {repeat_note}"
            f"Requires HR specialist review."
        )
        context = {
            "leave_request_id": leave_request.id,
            "leave_type": leave_type_code,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": float(days),
            "purpose": purpose,
            "is_repeat_within_12_months": is_repeat_within_12_months,
            "document_reference": document_reference,
        }
        # create_hitl_request() commits internally - that commit also
        # persists the leave_request flushed above, in the same transaction.
        hitl_result = hitl_service.create_hitl_request(
            request_type="UNPAID_LEAVE_REQUEST",
            query=query,
            related_entity_type="leave_request",
            related_entity_id=leave_request.id,
            employee_id=employee_id,
            context=context,
            priority="HIGH" if is_repeat_within_12_months else "MEDIUM"
        )

        # Phase 165 - the full review-lifecycle row, created at queue-entry
        # time (not just at resolution) so "elapsed time since submitted"
        # is always computable, and so hr_specialist_employee_id ends up a
        # real FK, not just a name string overloaded onto hitl_requests.assigned_to.
        # Phase 172 - task_state starts "input_required": by the time this
        # row is written, the calling agent graph has already run its own
        # intake/eligibility steps synchronously and is about to pause
        # waiting on the specialist - "submitted"/"working" only ever held
        # true transiently inside that same request, never durably here.
        review = SpecialistLeaveReview(
            hitl_request_id=hitl_result["hitlRequestId"],
            leave_request_id=leave_request.id,
            leave_type_code=leave_type_code,
            status=HitlRequestStatus.PENDING,
            task_state="input_required",
        )
        self.db.add(review)

        # Phase 165 - links the manifest row register_leave_document()
        # created at upload time (leave_request_id still null then) to the
        # leave request that just got created, closing the orphan-upload
        # gap: before this, a failed submit after a successful S3 upload
        # left nothing in any database pointing at the uploaded file.
        if document_reference:
            document = self.db.query(UnpaidLeaveDocument).filter(
                UnpaidLeaveDocument.s3_key == document_reference
            ).first()
            if document:
                document.leave_request_id = leave_request.id

        self.db.commit()

        return {
            "requestId": leave_request.id,
            "employeeId": employee_id,
            "leaveType": leave_type_code,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "days": float(days),
            "status": leave_request.status.value,
            "approverId": approver.employee_id if approver else None,
            "isRepeatWithin12Months": is_repeat_within_12_months,
            "hitlRequestId": hitl_result.get("hitlRequestId"),
            "hitlStatus": hitl_result.get("status"),
            "createdAt": leave_request.created_at.isoformat() if leave_request.created_at else None
        }

    def set_review_brief(self, hitl_request_id: int, review_brief: str) -> dict:
        """Phase 172 - stores the specialist-facing LLM-generated summary
        (the "Review-support agent" from the original design) onto the
        review row, right after it's generated and before the agent graph
        pauses - so it's already there the moment a specialist opens the
        queue, not generated on demand per view.

        Args:
            hitl_request_id: The HITL request this review brief belongs to
            review_brief: The generated plain-English summary text

        Returns:
            Dictionary confirming the write
        """
        review = self.db.query(SpecialistLeaveReview).filter(
            SpecialistLeaveReview.hitl_request_id == hitl_request_id
        ).first()
        if not review:
            raise ResourceNotFoundException(f"No specialist review found for HITL request ID: {hitl_request_id}")

        review.review_brief = review_brief
        self.db.commit()

        return {"hitlRequestId": hitl_request_id, "reviewBriefSet": True}

    def register_leave_document(
        self, employee_id: str, s3_key: str, original_filename: str, content_type: Optional[str] = None
    ) -> dict:
        """Phase 165 - creates the manifest row at upload time, before the
        leave request it will belong to exists yet (leave_request_id stays
        null until submit_unpaid_leave_request links it). This is what
        makes an uploaded file trackable even if submit never follows - the
        orphan-upload gap this phase closes.

        Args:
            employee_id: Employee ID (not stored on the row itself -
                validated here only to reject an unknown caller early)
            s3_key: The S3 object key the file was uploaded to
            original_filename: The file's original name, for display
            content_type: The file's MIME type, if known

        Returns:
            Dictionary with the new manifest row's id and s3_key
        """
        employee = self.db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise ResourceNotFoundException(f"Employee not found with ID: {employee_id}")

        document = UnpaidLeaveDocument(
            s3_key=s3_key,
            original_filename=original_filename,
            content_type=content_type,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        return {
            "documentId": document.id,
            "s3Key": document.s3_key,
            "originalFilename": document.original_filename,
            "uploadedAt": document.uploaded_at.isoformat() if document.uploaded_at else None,
        }

    def list_leave_documents(self, leave_request_id: int) -> dict:
        """Phase 165 - the manifest rows for one leave request's documents,
        used by both the HR review queue and the employee's own "My
        Requests" view to know what to request a download URL for.
        ownerEmployeeId is included so the caller (hrb_chatbot_v2's own
        download-URL route) can check ownership - is this caller the
        employee who filed the request, or an hr_support persona - without
        a 2nd round trip just to look that up."""
        leave_request = self.db.query(LeaveRequest).filter(LeaveRequest.id == leave_request_id).first()
        owner_employee_id = leave_request.employee.employee_id if leave_request and leave_request.employee else None

        documents = self.db.query(UnpaidLeaveDocument).filter(
            UnpaidLeaveDocument.leave_request_id == leave_request_id
        ).all()

        return {
            "leaveRequestId": leave_request_id,
            "ownerEmployeeId": owner_employee_id,
            "documents": [
                {
                    "documentId": document.id,
                    "s3Key": document.s3_key,
                    "originalFilename": document.original_filename,
                    "contentType": document.content_type,
                    "uploadedAt": document.uploaded_at.isoformat() if document.uploaded_at else None,
                }
                for document in documents
            ],
        }

    def list_my_leave_requests(self, employee_id: str, limit: Optional[int] = None, offset: Optional[int] = None) -> dict:
        """Phase 165 - the employee's own "My Requests" view: every
        specialist-reviewed leave request they've submitted, joined to its
        review's current status/comments/timestamps. Scoped to the
        caller's own employee_id only - same non-disclosure every other
        per-employee list in this project already follows."""
        employee = self.db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise ResourceNotFoundException(f"Employee not found with ID: {employee_id}")

        if limit is None or limit <= 0:
            limit = 20
        if offset is None or offset < 0:
            offset = 0

        query = self.db.query(LeaveRequest, SpecialistLeaveReview).join(
            SpecialistLeaveReview, SpecialistLeaveReview.leave_request_id == LeaveRequest.id
        ).filter(LeaveRequest.employee_id == employee.id)

        total = query.count()
        rows = query.order_by(desc(LeaveRequest.created_at)).offset(offset).limit(limit).all()

        items = []
        for leave_request, review in rows:
            specialist = review.hr_specialist if review.hr_specialist_employee_id else None
            items.append({
                "requestId": leave_request.id,
                "leaveType": review.leave_type_code,
                "startDate": leave_request.start_date.isoformat(),
                "endDate": leave_request.end_date.isoformat(),
                "days": float(leave_request.days),
                "purpose": leave_request.reason,
                "status": review.status.value,
                "decision": review.decision.value if review.decision else None,
                "hrComments": review.hr_comments,
                "hrSpecialistName": specialist.name if specialist else None,
                "hrSpecialistEmployeeId": specialist.employee_id if specialist else None,
                "createdAt": review.created_at.isoformat() if review.created_at else None,
                "respondedAt": review.responded_at.isoformat() if review.responded_at else None,
                # Phase 172
                "taskState": review.task_state,
                "reviewBrief": review.review_brief,
                "decisionMessage": review.decision_message,
                "producedArtifacts": review.produced_artifacts or [],
            })

        return {
            "employeeId": employee_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "requests": items,
        }

    def list_all_leave_requests(self, status: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> dict:
        """
        Phase 168 (round 2) - the HR specialist grid: every specialist-
        reviewed leave request across every employee, joined to its
        review's full status/decision/comments/timestamps - not just
        PENDING ones (that's what the existing list_hitl_requests tool,
        used by /pending, already does). Same join as
        list_my_leave_requests() above, minus the employee_id filter, plus
        employeeId/employeeName and hitlRequestId (needed for the HR
        grid's own click-through to resolve_hitl_request) that the
        employee-facing version has no reason to expose.

        Args:
            status: Filter by review status (PENDING, IN_PROGRESS, COMPLETED, CANCELLED, or 'all'/None for every status)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            Every matching leave request, newest-submitted-first
        """
        if limit is None or limit <= 0:
            limit = 50
        if offset is None or offset < 0:
            offset = 0

        query = self.db.query(LeaveRequest, SpecialistLeaveReview).join(
            SpecialistLeaveReview, SpecialistLeaveReview.leave_request_id == LeaveRequest.id
        )

        status_filter = (status or "ALL").upper().strip()
        if status_filter != "ALL":
            try:
                query = query.filter(SpecialistLeaveReview.status == HitlRequestStatus[status_filter])
            except KeyError:
                valid_statuses = [s.name for s in HitlRequestStatus]
                raise BusinessException(
                    "INVALID_STATUS",
                    f"Invalid status: {status}. Valid values are: {', '.join(valid_statuses)}, or 'all' (no filter)"
                )

        total = query.count()
        rows = query.order_by(desc(LeaveRequest.created_at)).offset(offset).limit(limit).all()

        items = []
        for leave_request, review in rows:
            specialist = review.hr_specialist if review.hr_specialist_employee_id else None
            employee = leave_request.employee
            items.append({
                "hitlRequestId": review.hitl_request_id,
                "requestId": leave_request.id,
                "employeeId": employee.employee_id if employee else None,
                "employeeName": employee.name if employee else None,
                "leaveType": review.leave_type_code,
                "startDate": leave_request.start_date.isoformat(),
                "endDate": leave_request.end_date.isoformat(),
                "days": float(leave_request.days),
                "purpose": leave_request.reason,
                "status": review.status.value,
                "decision": review.decision.value if review.decision else None,
                "hrComments": review.hr_comments,
                "hrSpecialistName": specialist.name if specialist else None,
                "hrSpecialistEmployeeId": specialist.employee_id if specialist else None,
                "createdAt": review.created_at.isoformat() if review.created_at else None,
                "respondedAt": review.responded_at.isoformat() if review.responded_at else None,
                # Phase 172
                "taskState": review.task_state,
                "reviewBrief": review.review_brief,
                "decisionMessage": review.decision_message,
                "producedArtifacts": review.produced_artifacts or [],
            })

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "requests": items,
        }

    def get_leave_history(
        self,
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
            year: Year filter (optional, filters by start_date year)
            status: Status filter (optional)
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            Dictionary with leave history
        """
        # Get employee
        employee = self.db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise ResourceNotFoundException(f"Employee not found with ID: {employee_id}")
        
        if limit is None or limit <= 0:
            limit = 10
        if offset is None or offset < 0:
            offset = 0
        
        # Build query
        query = self.db.query(LeaveRequest).filter(LeaveRequest.employee_id == employee.id)
        
        # Filter by year if provided
        if year is not None:
            query = query.filter(extract('year', LeaveRequest.start_date) == year)
        
        # Filter by status if provided (handle 'all' as no filter)
        if status:
            status_upper = status.upper().strip()
            # Handle 'all' as a special case meaning no status filter
            if status_upper == 'ALL':
                # No status filter applied
                pass
            else:
                try:
                    status_enum = LeaveRequestStatus[status_upper]
                    query = query.filter(LeaveRequest.status == status_enum)
                except KeyError:
                    valid_statuses = [s.name for s in LeaveRequestStatus]
                    raise BusinessException(
                        "INVALID_STATUS",
                        f"Invalid status: {status}. Valid values are: {', '.join(valid_statuses)}, or 'all' (no filter)"
                    )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        requests = query.order_by(desc(LeaveRequest.created_at)).offset(offset).limit(limit).all()
        
        # Format response
        request_items = []
        for req in requests:
            request_items.append({
                "requestId": req.id,
                "leaveType": req.leave_type.code,
                "startDate": req.start_date.isoformat(),
                "endDate": req.end_date.isoformat(),
                "days": float(req.days),
                "status": req.status.value,
                "approvedAt": req.approved_at.isoformat() if req.approved_at else None,
                "createdAt": req.created_at.isoformat() if req.created_at else None
            })
        
        return {
            "employeeId": employee_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "requests": request_items
        }
    
    def get_pending_approvals(self, manager_id: str) -> dict:
        """
        Get pending leave approvals for a manager.
        
        Args:
            manager_id: Manager employee ID
            
        Returns:
            Dictionary with pending approvals
        """
        # Get manager
        manager = self.db.query(Employee).filter(Employee.employee_id == manager_id).first()
        if not manager:
            raise ResourceNotFoundException(f"Manager not found with ID: {manager_id}")
        
        # Get pending requests
        pending_requests = self.db.query(LeaveRequest).filter(
            and_(
                LeaveRequest.approver_id == manager.id,
                LeaveRequest.status == LeaveRequestStatus.PENDING
            )
        ).all()
        
        # Format response
        approvals = []
        for req in pending_requests:
            approvals.append({
                "requestId": req.id,
                "employeeId": req.employee.employee_id,
                "employeeName": req.employee.name,
                "leaveType": req.leave_type.code,
                "startDate": req.start_date.isoformat(),
                "endDate": req.end_date.isoformat(),
                "days": float(req.days),
                "reason": req.reason,
                "submittedAt": req.created_at.isoformat() if req.created_at else None
            })
        
        return {
            "managerId": manager_id,
            "total": len(approvals),
            "approvals": approvals
        }


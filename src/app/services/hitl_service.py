"""HITL service."""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from src.app.models.models import (
    HitlRequest, Employee, LeaveType, HitlRequestStatus, LeaveRequest, LeaveRequestStatus,
    SpecialistLeaveReview, LeaveReviewDecision, UnpaidLeaveDocument
)
from src.app.exceptions.exceptions import ResourceNotFoundException, BusinessException
from decimal import Decimal


class HitlService:
    """Service for managing HITL requests."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_hitl_request_for_leave_exception(
        self,
        employee: Employee,
        leave_type: LeaveType,
        requested_days: Decimal,
        available_balance: Decimal,
        leave_request_id: int
    ) -> dict:
        """
        Create HITL request for leave exception.
        
        Args:
            employee: Employee object
            leave_type: Leave type object
            requested_days: Requested days
            available_balance: Available balance
            leave_request_id: Leave request ID
            
        Returns:
            Dictionary with HITL request details
        """
        shortfall = requested_days - available_balance
        
        context = {
            "leave_request_id": leave_request_id,
            "requested_days": float(requested_days),
            "available_balance": float(available_balance),
            "shortfall": float(shortfall),
            "leave_type": leave_type.code,
        }
        
        query = (
            f"Employee {employee.name} requests {requested_days} days {leave_type.name} "
            f"but only has {available_balance} days available. Requires exception approval."
        )
        
        hitl_request = HitlRequest(
            request_type="LEAVE_EXCEPTION",
            related_entity_type="leave_request",
            related_entity_id=leave_request_id,
            employee_id=employee.id,
            query=query,
            context=context,
            status=HitlRequestStatus.PENDING,
            assigned_to="hr-team@company.com"
        )
        
        self.db.add(hitl_request)
        self.db.commit()
        self.db.refresh(hitl_request)
        
        return {
            "hitlRequestId": hitl_request.id,
            "requestType": hitl_request.request_type,
            "status": hitl_request.status.value,
            "assignedTo": hitl_request.assigned_to,
            "notificationSent": True,
            "query": hitl_request.query,
            "context": hitl_request.context,
            "createdAt": hitl_request.created_at.isoformat() if hitl_request.created_at else None
        }
    
    def create_hitl_request(
        self,
        request_type: str,
        query: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        employee_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: Optional[str] = None
    ) -> dict:
        """
        Create a HITL request.
        
        Args:
            request_type: Request type
            query: Query or request description
            related_entity_type: Related entity type
            related_entity_id: Related entity ID
            employee_id: Employee ID
            context: Additional context
            priority: Priority
            
        Returns:
            Dictionary with HITL request details
        """
        employee = None
        if employee_id:
            employee = self.db.query(Employee).filter(Employee.employee_id == employee_id).first()
            if not employee:
                raise ResourceNotFoundException(f"Employee not found with ID: {employee_id}")
        
        hitl_request = HitlRequest(
            request_type=request_type,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            employee_id=employee.id if employee else None,
            query=query,
            context=context,
            status=HitlRequestStatus.PENDING,
            assigned_to="hr-team@company.com"
        )
        
        self.db.add(hitl_request)
        self.db.commit()
        self.db.refresh(hitl_request)
        
        return {
            "hitlRequestId": hitl_request.id,
            "requestType": hitl_request.request_type,
            "status": hitl_request.status.value,
            "assignedTo": hitl_request.assigned_to,
            "notificationSent": True,
            "query": hitl_request.query,
            "context": hitl_request.context,
            "createdAt": hitl_request.created_at.isoformat() if hitl_request.created_at else None,
            "updatedAt": hitl_request.updated_at.isoformat() if hitl_request.updated_at else None
        }
    
    def get_hitl_request(self, hitl_request_id: int) -> dict:
        """
        Get HITL request by ID.
        
        Args:
            hitl_request_id: HITL request ID
            
        Returns:
            Dictionary with HITL request details
        """
        hitl_request = self.db.query(HitlRequest).filter(HitlRequest.id == hitl_request_id).first()
        if not hitl_request:
            raise ResourceNotFoundException(f"HITL request not found with ID: {hitl_request_id}")
        
        return {
            "hitlRequestId": hitl_request.id,
            "requestType": hitl_request.request_type,
            "status": hitl_request.status.value,
            "assignedTo": hitl_request.assigned_to,
            "notificationSent": False,
            "query": hitl_request.query,
            "context": hitl_request.context,
            "response": hitl_request.response,
            "respondedAt": hitl_request.responded_at.isoformat() if hitl_request.responded_at else None,
            "createdAt": hitl_request.created_at.isoformat() if hitl_request.created_at else None,
            "updatedAt": hitl_request.updated_at.isoformat() if hitl_request.updated_at else None
        }

    def resolve_hitl_request(
        self,
        hitl_request_id: int,
        decision: str,
        response_text: str,
        resolved_by: Optional[str] = None,
        resolved_by_employee_id: Optional[str] = None
    ) -> dict:
        """
        Resolve a HITL request with a human decision - approve or reject.

        This is the missing half of the HITL loop: create_hitl_request() and
        get_hitl_request() already existed, but nothing anywhere wrote to
        response/responded_at or moved status out of PENDING. When the
        request is tied to a leave request (related_entity_type ==
        "leave_request"), that leave request's own status is updated in the
        same transaction, so the two never drift out of sync.

        Phase 165: also updates the matching SpecialistLeaveReview row, if
        one exists for this hitl_request_id (only leave requests that went
        through submit_unpaid_leave_request have one - other HITL request
        types, e.g. LEAVE_EXCEPTION, don't). resolved_by_employee_id is a
        real employee_id, separate from resolved_by (which stays a display-
        name string written onto hitl_requests.assigned_to, unchanged
        behavior) - it's what lets the review row carry a real FK to
        employees instead of only a name.

        Args:
            hitl_request_id: HITL request ID
            decision: APPROVED or REJECTED
            response_text: The specialist's explanation/notes for this decision
            resolved_by: Identifier of the specialist who resolved this, e.g. an email or display name
            resolved_by_employee_id: The resolving specialist's own employee_id, if known

        Returns:
            Dictionary with the resolved HITL request details
        """
        hitl_request = self.db.query(HitlRequest).filter(HitlRequest.id == hitl_request_id).first()
        if not hitl_request:
            raise ResourceNotFoundException(f"HITL request not found with ID: {hitl_request_id}")

        if hitl_request.status == HitlRequestStatus.COMPLETED:
            raise BusinessException(
                "ALREADY_RESOLVED",
                f"HITL request {hitl_request_id} was already resolved at "
                f"{hitl_request.responded_at.isoformat() if hitl_request.responded_at else 'an earlier time'}"
            )

        decision_upper = decision.upper().strip()
        if decision_upper not in ("APPROVED", "REJECTED"):
            raise BusinessException("INVALID_DECISION", f"decision must be APPROVED or REJECTED, got: {decision!r}")

        hitl_request.status = HitlRequestStatus.COMPLETED
        hitl_request.response = response_text
        hitl_request.responded_at = datetime.utcnow()
        if resolved_by:
            hitl_request.assigned_to = resolved_by

        related_leave_request_updated = False
        if hitl_request.related_entity_type == "leave_request" and hitl_request.related_entity_id:
            leave_request = self.db.query(LeaveRequest).filter(
                LeaveRequest.id == hitl_request.related_entity_id
            ).first()
            if leave_request:
                if decision_upper == "APPROVED":
                    leave_request.status = LeaveRequestStatus.APPROVED
                    leave_request.approved_at = datetime.utcnow()
                else:
                    leave_request.status = LeaveRequestStatus.REJECTED
                    leave_request.rejection_reason = response_text
                related_leave_request_updated = True

        review = self.db.query(SpecialistLeaveReview).filter(
            SpecialistLeaveReview.hitl_request_id == hitl_request_id
        ).first()
        if review:
            review.status = HitlRequestStatus.COMPLETED
            review.decision = LeaveReviewDecision[decision_upper]
            review.hr_comments = response_text
            review.responded_at = datetime.utcnow()
            # Phase 172 - A2A-shaped Task state + the decision captured as a
            # Message/Parts structure, alongside the existing plain columns
            # above (which stay authoritative for every pre-172 caller).
            review.task_state = "completed" if decision_upper == "APPROVED" else "rejected"
            review.decision_message = {
                "role": "specialist",
                "parts": [{"type": "text", "content": response_text}],
            }
            if resolved_by_employee_id:
                specialist = self.db.query(Employee).filter(Employee.employee_id == resolved_by_employee_id).first()
                if specialist:
                    review.hr_specialist_employee_id = specialist.id

        self.db.commit()
        self.db.refresh(hitl_request)

        return {
            "hitlRequestId": hitl_request.id,
            "status": hitl_request.status.value,
            "decision": decision_upper,
            "response": hitl_request.response,
            "respondedAt": hitl_request.responded_at.isoformat() if hitl_request.responded_at else None,
            "assignedTo": hitl_request.assigned_to,
            "relatedLeaveRequestUpdated": related_leave_request_updated,
            "employeeEmail": hitl_request.employee.email if hitl_request.employee else None,
        }

    def record_produced_artifact(self, hitl_request_id: int, artifact: Dict[str, Any]) -> dict:
        """Phase 172 - appends one Artifact-shaped record (e.g. the decision
        email) to the review row, called by hrb_chatbot_v2 right after it
        actually sends that email - this repo has no email client of its
        own, so it can't record this at resolve_hitl_request() time; the
        artifact is produced one call later, by a different service.

        Args:
            hitl_request_id: The HITL request this artifact belongs to
            artifact: Plain dict describing what was produced, e.g.
                {"type": "email", "recipient": "...", "sent": true, "sent_at": "..."}

        Returns:
            Dictionary confirming the write
        """
        review = self.db.query(SpecialistLeaveReview).filter(
            SpecialistLeaveReview.hitl_request_id == hitl_request_id
        ).first()
        if not review:
            raise ResourceNotFoundException(f"No specialist review found for HITL request ID: {hitl_request_id}")

        review.produced_artifacts = [*(review.produced_artifacts or []), artifact]
        self.db.commit()

        return {"hitlRequestId": hitl_request_id, "artifactRecorded": True}

    def list_hitl_requests(
        self,
        status: Optional[str] = None,
        request_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> dict:
        """
        List HITL requests, optionally filtered by status and/or request
        type - needed for a specialist review queue to show what's actually
        pending. create_hitl_request()/get_hitl_request() only ever
        operated on one known ID; nothing could list requests before this.

        Args:
            status: Filter by status (PENDING, IN_PROGRESS, COMPLETED, CANCELLED, or 'all' for no filter) - defaults to PENDING
            request_type: Filter by request type (e.g. UNPAID_LEAVE_REQUEST, LEAVE_EXCEPTION) - optional
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            Dictionary with the matching HITL requests
        """
        if limit is None or limit <= 0:
            limit = 20
        if offset is None or offset < 0:
            offset = 0

        query = self.db.query(HitlRequest)

        status_filter = (status or "PENDING").upper().strip()
        if status_filter != "ALL":
            try:
                status_enum = HitlRequestStatus[status_filter]
                query = query.filter(HitlRequest.status == status_enum)
            except KeyError:
                valid_statuses = [s.name for s in HitlRequestStatus]
                raise BusinessException(
                    "INVALID_STATUS",
                    f"Invalid status: {status}. Valid values are: {', '.join(valid_statuses)}, or 'all' (no filter)"
                )

        if request_type:
            query = query.filter(HitlRequest.request_type == request_type)

        total = query.count()
        hitl_requests = query.order_by(desc(HitlRequest.created_at)).offset(offset).limit(limit).all()

        items = []
        for hitl_request in hitl_requests:
            items.append({
                "hitlRequestId": hitl_request.id,
                "requestType": hitl_request.request_type,
                "relatedEntityType": hitl_request.related_entity_type,
                "relatedEntityId": hitl_request.related_entity_id,
                "employeeId": hitl_request.employee.employee_id if hitl_request.employee else None,
                "query": hitl_request.query,
                "context": hitl_request.context,
                "status": hitl_request.status.value,
                "assignedTo": hitl_request.assigned_to,
                "createdAt": hitl_request.created_at.isoformat() if hitl_request.created_at else None
            })

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "requests": items
        }

    def admin_delete_hitl_request(self, hitl_request_id: int) -> dict:
        """
        Phase 168 - hard-deletes a HITL request and everything that hangs
        off it, in FK-safe order. For an admin "clean up test data" tool,
        not a normal application flow - no other method in this repo
        deletes anything at all before this one.

        Deletion order (children before parents, to satisfy FK
        constraints that have no ON DELETE CASCADE):
          1. SpecialistLeaveReview row(s) for this hitl_request_id
          2. UnpaidLeaveDocument row(s) for the related leave_request_id
             (their s3_key values are returned, not deleted here - this
             repo has no AWS/S3 client of its own; the caller, which does,
             deletes the real objects)
          3. The related LeaveRequest row, if related_entity_type ==
             "leave_request"
          4. The HitlRequest row itself

        Args:
            hitl_request_id: HITL request ID to delete, with everything
                that hangs off it

        Returns:
            What was deleted - counts and the S3 keys the caller still
            needs to clean up
        """
        hitl_request = self.db.query(HitlRequest).filter(HitlRequest.id == hitl_request_id).first()
        if not hitl_request:
            raise ResourceNotFoundException(f"HITL request not found with ID: {hitl_request_id}")

        deleted_reviews = self.db.query(SpecialistLeaveReview).filter(
            SpecialistLeaveReview.hitl_request_id == hitl_request_id
        ).delete(synchronize_session=False)

        deleted_documents_s3_keys: list[str] = []
        deleted_leave_request = False
        if hitl_request.related_entity_type == "leave_request" and hitl_request.related_entity_id:
            leave_request_id = hitl_request.related_entity_id
            documents = self.db.query(UnpaidLeaveDocument).filter(
                UnpaidLeaveDocument.leave_request_id == leave_request_id
            ).all()
            deleted_documents_s3_keys = [document.s3_key for document in documents]
            for document in documents:
                self.db.delete(document)

            leave_request = self.db.query(LeaveRequest).filter(LeaveRequest.id == leave_request_id).first()
            if leave_request:
                self.db.delete(leave_request)
                deleted_leave_request = True

        self.db.delete(hitl_request)
        self.db.commit()

        return {
            "hitlRequestId": hitl_request_id,
            "deletedHitlRequest": True,
            "deletedSpecialistLeaveReviews": deleted_reviews,
            "deletedLeaveRequest": deleted_leave_request,
            "deletedDocumentS3Keys": deleted_documents_s3_keys,
        }


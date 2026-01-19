"""Leave request service."""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, date
from decimal import Decimal
from src.app.models.models import (
    Employee, LeaveRequest, LeaveType, LeaveBalance,
    LeaveRequestStatus
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
    
    def get_leave_history(
        self,
        employee_id: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> dict:
        """
        Get leave request history for an employee.
        
        Args:
            employee_id: Employee ID
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
        
        if status:
            try:
                status_enum = LeaveRequestStatus[status.upper()]
                query = query.filter(LeaveRequest.status == status_enum)
            except KeyError:
                raise BusinessException("INVALID_STATUS", f"Invalid status: {status}")
        
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


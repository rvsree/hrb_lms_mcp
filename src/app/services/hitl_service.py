"""HITL service."""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from src.app.models.models import HitlRequest, Employee, LeaveType, HitlRequestStatus
from src.app.exceptions.exceptions import ResourceNotFoundException
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


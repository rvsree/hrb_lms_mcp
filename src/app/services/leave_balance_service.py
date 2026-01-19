"""Leave balance service."""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from src.app.models.models import Employee, LeaveBalance, LeaveType
from src.app.exceptions.exceptions import ResourceNotFoundException


class LeaveBalanceService:
    """Service for managing leave balances."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_leave_balance(self, employee_id: str, year: Optional[int] = None) -> dict:
        """
        Get leave balance for an employee.
        
        Args:
            employee_id: Employee ID
            year: Year (optional, defaults to current year)
            
        Returns:
            Dictionary with leave balance details
        """
        if year is None:
            year = datetime.now().year
        
        # Get employee
        employee = self.db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not employee:
            raise ResourceNotFoundException(f"Employee not found with ID: {employee_id}")
        
        # Get leave balances for the year
        balances = self.db.query(LeaveBalance).join(LeaveType).filter(
            and_(
                LeaveBalance.employee_id == employee.id,
                LeaveBalance.year == year
            )
        ).all()
        
        # Format response
        balance_details = []
        for balance in balances:
            balance_details.append({
                "leaveType": balance.leave_type.code,
                "leaveTypeName": balance.leave_type.name,
                "accrued": float(balance.accrued) if balance.accrued else 0.0,
                "used": float(balance.used) if balance.used else 0.0,
                "available": float(balance.available) if balance.available else 0.0,
            })
        
        return {
            "employeeId": employee_id,
            "year": year,
            "balances": balance_details
        }


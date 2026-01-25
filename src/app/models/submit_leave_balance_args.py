from pydantic import BaseModel, Field, ValidationError
from typing import Optional


class SubmitLeaveRequestArgs(BaseModel):
    """Arguments for submit_leave_request tool."""
    employee_id: str = Field(..., description="Employee ID")
    leave_type: str = Field(..., description="Leave type (PTO, SICK, UNPAID, etc.)")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    reason: Optional[str] = Field(None, description="Reason for leave")
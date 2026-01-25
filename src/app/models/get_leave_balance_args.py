from pydantic import BaseModel, Field, ValidationError
from typing import Optional


class GetLeaveBalanceArgs(BaseModel):
    """Arguments for get_leave_balance tool."""
    employee_id: str = Field(..., description="Employee ID (required)")
    year: Optional[int] = Field(None, description="Year for leave balance (optional, defaults to current year)")
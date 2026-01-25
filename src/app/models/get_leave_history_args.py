from pydantic import BaseModel, Field, ValidationError
from typing import Optional


class GetLeaveHistoryArgs(BaseModel):
    """Arguments for get_leave_history tool."""
    employee_id: str = Field(..., description="Employee ID")
    year: Optional[int] = Field(None, description="Year for which to retrieve leave history (e.g., 2025, 2026). If not specified, returns all years.")
    status: Optional[str] = Field(None, description="Filter by status. Valid values: PENDING, APPROVED, REJECTED, PENDING_HITL, or 'all' to return all statuses. If not specified, returns all statuses.")
    limit: Optional[int] = Field(None, description="Maximum number of results")
    offset: Optional[int] = Field(None, description="Offset for pagination")
from pydantic import BaseModel, Field
from typing import Optional


class ListMyLeaveRequestsArgs(BaseModel):
    """Arguments for list_my_leave_requests tool."""
    employee_id: str = Field(..., description="Employee ID - returns only their own requests")
    limit: Optional[int] = Field(None, description="Maximum number of results")
    offset: Optional[int] = Field(None, description="Offset for pagination")

from pydantic import BaseModel, Field
from typing import Optional


class ListAllLeaveRequestsArgs(BaseModel):
    """Arguments for list_all_leave_requests tool."""
    status: Optional[str] = Field(None, description="Filter by review status, or 'all'/None for every status")
    limit: Optional[int] = Field(None, description="Maximum number of results")
    offset: Optional[int] = Field(None, description="Offset for pagination")

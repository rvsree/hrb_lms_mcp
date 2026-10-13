from pydantic import BaseModel, Field
from typing import Optional


class ListHITLRequestsArgs(BaseModel):
    """Arguments for list_hitl_requests tool."""
    status: Optional[str] = Field(None, description="Filter by status (PENDING, IN_PROGRESS, COMPLETED, CANCELLED, or 'all'). Defaults to PENDING.")
    request_type: Optional[str] = Field(None, description="Filter by request type, e.g. UNPAID_LEAVE_REQUEST")
    limit: Optional[int] = Field(None, description="Maximum number of results")
    offset: Optional[int] = Field(None, description="Offset for pagination")

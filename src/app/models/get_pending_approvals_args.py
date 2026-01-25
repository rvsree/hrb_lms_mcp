from pydantic import BaseModel, Field, ValidationError
from typing import Optional


class GetPendingApprovalsArgs(BaseModel):
    """Arguments for get_pending_approvals tool."""
    manager_id: str = Field(..., description="Manager employee ID")
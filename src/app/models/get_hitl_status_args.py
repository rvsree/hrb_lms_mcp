from pydantic import BaseModel, Field, ValidationError
from typing import Optional


class GetHITLStatusArgs(BaseModel):
    """Arguments for get_hitl_status tool."""
    hitl_request_id: int = Field(..., description="HITL request ID")
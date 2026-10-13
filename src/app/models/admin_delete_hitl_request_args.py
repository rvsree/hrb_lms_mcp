from pydantic import BaseModel, Field


class AdminDeleteHitlRequestArgs(BaseModel):
    """Arguments for admin_delete_hitl_request tool."""
    hitl_request_id: int = Field(..., description="HITL request ID to hard-delete, with everything that hangs off it")

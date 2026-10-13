from pydantic import BaseModel, Field
from typing import Optional


class ResolveHITLRequestArgs(BaseModel):
    """Arguments for resolve_hitl_request tool."""
    hitl_request_id: int = Field(..., description="HITL request ID to resolve")
    decision: str = Field(..., description="APPROVED or REJECTED")
    response_text: str = Field(..., description="The specialist's explanation/notes for this decision")
    resolved_by: Optional[str] = Field(None, description="Identifier of the specialist who resolved this, e.g. an email")
    resolved_by_employee_id: Optional[str] = Field(None, description="Phase 165 - the resolving specialist's own employee_id, if known")

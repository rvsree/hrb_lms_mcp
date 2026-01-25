from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Dict, Any


class CreateHITLRequestArgs(BaseModel):
    """Arguments for create_hitl_request tool."""
    request_type: str = Field(..., description="Request type (LEAVE_EXCEPTION, POLICY_INTERPRETATION, etc.)")
    query: str = Field(..., description="Query or request description")
    related_entity_type: Optional[str] = Field(None, description="Related entity type (leave_request, employee, etc.)")
    related_entity_id: Optional[int] = Field(None, description="Related entity ID")
    employee_id: Optional[str] = Field(None, description="Employee ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    priority: Optional[str] = Field(None, description="Priority (LOW, MEDIUM, HIGH)")
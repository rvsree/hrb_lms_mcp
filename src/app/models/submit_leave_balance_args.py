from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Optional, Literal


# Valid leave types in the database
VALID_LEAVE_TYPES = ["PTO", "SICK"]


class SubmitLeaveRequestArgs(BaseModel):
    """Arguments for submit_leave_request tool."""
    employee_id: str = Field(..., description="Employee ID")
    leave_type: str = Field(
        ..., 
        description="Leave type code. MUST be 'PTO' (Paid Time Off) or 'SICK' (Sick Leave for illness/medical). "
                    "Use SICK for medical appointments, surgery, illness recovery."
    )
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    reason: Optional[str] = Field(None, description="Reason for leave")
    
    @field_validator('leave_type')
    @classmethod
    def validate_leave_type(cls, v: str) -> str:
        """Validate and normalize leave type."""
        normalized = v.upper().strip()
        # Map common alternatives to valid types
        mapping = {
            "MEDICAL": "SICK",
            "VACATION": "PTO",
            "PERSONAL": "PTO",
            "ANNUAL": "PTO",
            "HOLIDAY": "PTO",
        }
        if normalized in mapping:
            return mapping[normalized]
        if normalized not in VALID_LEAVE_TYPES:
            raise ValueError(f"Invalid leave_type '{v}'. Must be one of: {VALID_LEAVE_TYPES}")
        return normalized
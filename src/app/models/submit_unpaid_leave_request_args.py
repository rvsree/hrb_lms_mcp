from pydantic import BaseModel, Field
from typing import Optional


class SubmitUnpaidLeaveRequestArgs(BaseModel):
    """Arguments for submit_unpaid_leave_request tool."""
    employee_id: str = Field(..., description="Employee ID")
    start_date: str = Field(..., description="Leave start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Leave end date (YYYY-MM-DD)")
    purpose: str = Field(..., description="Reason/purpose for the unpaid leave request")
    is_repeat_within_12_months: bool = Field(
        ..., description="Whether the employee has taken this same leave type within the last 12 months - computed by the caller from get_leave_history, not re-derived here"
    )
    leave_type_code: str = Field("UNPAID", description="Phase 165 - UNPAID, CRITICAL_CAREGIVER, STD, or LTD")
    document_reference: Optional[str] = Field(None, description="S3 key of a supporting document, if one was uploaded (already registered via register_leave_document)")

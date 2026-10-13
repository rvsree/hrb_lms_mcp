from pydantic import BaseModel, Field


class SetReviewBriefArgs(BaseModel):
    """Arguments for set_review_brief tool."""
    hitl_request_id: int = Field(..., description="HITL request ID this review brief belongs to")
    review_brief: str = Field(..., min_length=1, description="The generated plain-English summary for the specialist")

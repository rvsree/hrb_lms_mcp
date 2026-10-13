from pydantic import BaseModel, Field


class ListLeaveDocumentsArgs(BaseModel):
    """Arguments for list_leave_documents tool."""
    leave_request_id: int = Field(..., description="The leave request whose uploaded documents to list")

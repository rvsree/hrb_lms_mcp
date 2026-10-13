from pydantic import BaseModel, Field
from typing import Optional


class RegisterLeaveDocumentArgs(BaseModel):
    """Arguments for register_leave_document tool."""
    employee_id: str = Field(..., description="Employee ID")
    s3_key: str = Field(..., description="The S3 object key the file was uploaded to")
    original_filename: str = Field(..., description="The file's original name, for display")
    content_type: Optional[str] = Field(None, description="The file's MIME type, if known")

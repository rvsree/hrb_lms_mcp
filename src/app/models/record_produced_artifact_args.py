from typing import Any, Dict

from pydantic import BaseModel, Field


class RecordProducedArtifactArgs(BaseModel):
    """Arguments for record_produced_artifact tool."""
    hitl_request_id: int = Field(..., description="HITL request ID this artifact belongs to")
    artifact: Dict[str, Any] = Field(..., description="Plain dict describing what was produced, e.g. a sent email")

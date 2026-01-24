from typing import Optional, Dict, Any
from pydantic import BaseModel
from src.app.models.mcp_error import McpError


class McpResponse(BaseModel):
    """JSON-RPC 2.0 response."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[McpError] = None
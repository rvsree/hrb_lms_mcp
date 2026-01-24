from typing import Optional, Dict, Any
from pydantic import BaseModel


# Pydantic models for JSON-RPC 2.0
class McpRequest(BaseModel):
    """JSON-RPC 2.0 request."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str
    params: Optional[Dict[str, Any]] = None
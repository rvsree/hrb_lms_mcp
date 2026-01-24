from typing import Optional, Dict, Any
from pydantic import BaseModel

class McpError(BaseModel):
    """JSON-RPC 2.0 error."""
    code: int
    message: str
    data: Optional[Any] = None

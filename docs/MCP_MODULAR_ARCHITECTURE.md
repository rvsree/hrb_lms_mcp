# MCP Modular Architecture

## Overview

This document describes the modular architecture of the HRB LMS MCP Server, following MCP (Model Context Protocol) best practices and FastMCP design patterns.

## Architecture Principles

1. **Separation of Concerns**: Server configuration, tool definitions, and utilities are in separate modules
2. **Single Source of Truth**: FastMCP server instance is defined once in `mcp_server.py`
3. **Modular Design**: Each module has a clear, focused responsibility
4. **Maintainability**: Easy to add new tools, modify configuration, or extend functionality

## File Structure

```
src/app/api/
├── main.py                 # Entry point - imports app and registers tools
├── mcp_server.py          # FastMCP server instance and configuration
├── mcp_helpers.py         # Utility functions for MCP operations
└── controller/
    └── lms_mcp_tools.py   # MCP tool definitions
```

## Module Responsibilities

### 1. `mcp_server.py` - Server Configuration

**Purpose**: Central FastMCP server instance and configuration

**Responsibilities**:
- Initialize FastMCP server instance (`mcp = FastMCP("lms")`)
- Configure server settings (stateless HTTP, JSON responses)
- Define request logging middleware
- Create and export the FastMCP streamable HTTP app

**Key Components**:
- `mcp`: FastMCP server instance (imported by tools)
- `app`: FastMCP streamable HTTP application (imported by main.py)
- `MCPRequestLoggingMiddleware`: Middleware for request observability
- `create_mcp_app()`: Factory function to create configured app

**Usage**:
```python
from src.app.api.mcp_server import mcp, app

# Tools import mcp to register themselves
@mcp.tool()
def my_tool():
    pass

# main.py imports app to run the server
from src.app.api.mcp_server import app
```

### 2. `lms_mcp_tools.py` - Tool Definitions

**Purpose**: Define all MCP tools for the Leave Management System

**Responsibilities**:
- Import FastMCP server instance from `mcp_server`
- Define tool functions with `@mcp.tool()` decorator
- Implement tool logic (validation, service calls, error handling)
- Return tool results

**Key Components**:
- Tool functions: `get_leave_balance()`, `submit_leave_request()`, etc.
- Each tool:
  - Accepts individual parameters (not dict)
  - Validates using Pydantic models
  - Calls business services
  - Returns structured results
  - Handles errors appropriately

**Usage**:
```python
from src.app.api.mcp_server import mcp

@mcp.tool()
def get_leave_balance(employee_id: str, year: Optional[int] = None) -> dict:
    # Tool implementation
    pass
```

### 3. `mcp_helpers.py` - Utility Functions

**Purpose**: Reusable helper functions for MCP operations

**Responsibilities**:
- Database session management
- Response formatting
- Validation helpers
- Error handling utilities

**Key Components**:
- `get_db_session()`: Context manager for database sessions
- `format_error_response()`: Standardize error responses
- `validate_required_fields()`: Field validation helper
- `sanitize_response()`: Remove sensitive data from responses

**Usage**:
```python
from src.app.api.mcp_helpers import get_db_session, format_error_response

with get_db_session() as db:
    # Use database session
    pass
```

### 4. `main.py` - Entry Point

**Purpose**: Application entry point and server startup

**Responsibilities**:
- Import FastMCP app from `mcp_server`
- Import tools module to register all tools
- Configure logging
- Start uvicorn server

**Key Components**:
- Imports `app` from `mcp_server`
- Imports `lms_mcp_tools` to trigger tool registration
- `main()` function to run uvicorn server

**Usage**:
```bash
# Run directly
python -m src.app.api.main

# Or with uvicorn
uvicorn src.app.api.main:app --host 0.0.0.0 --port 8190
```

## Import Flow

```
main.py
  ├── imports app from mcp_server.py
  └── imports lms_mcp_tools.py (registers tools)
      └── imports mcp from mcp_server.py
          └── tools use @mcp.tool() decorator
```

## Benefits of This Architecture

1. **Clear Separation**: Each module has a single, well-defined responsibility
2. **Easy Testing**: Each module can be tested independently
3. **Maintainability**: Changes to server config don't affect tool definitions
4. **Scalability**: Easy to add new tools without modifying server configuration
5. **Reusability**: Helper functions can be used across multiple tools
6. **Standards Compliance**: Follows FastMCP and MCP best practices

## Comparison with Previous Structure

### Before (Monolithic)
- `main.py`: Server setup, middleware, and app creation
- `lms_mcp_tools.py`: Server instance, configuration, and all tools

**Issues**:
- Server configuration mixed with tool definitions
- No separation of concerns
- Harder to test and maintain

### After (Modular)
- `mcp_server.py`: Server instance and configuration only
- `lms_mcp_tools.py`: Tool definitions only (imports server)
- `mcp_helpers.py`: Reusable utilities
- `main.py`: Entry point only

**Benefits**:
- Clear module boundaries
- Single source of truth for server configuration
- Easy to extend and maintain

## Adding New Tools

1. **Add tool function** to `lms_mcp_tools.py`:
   ```python
   @mcp.tool()
   def new_tool(param1: str, param2: Optional[int] = None) -> dict:
       # Implementation
       pass
   ```

2. **Use helpers** from `mcp_helpers.py` if needed:
   ```python
   from src.app.api.mcp_helpers import get_db_session
   
   @mcp.tool()
   def new_tool(param: str) -> dict:
       with get_db_session() as db:
           # Use db
           pass
   ```

3. **No changes needed** to `mcp_server.py` or `main.py` - tools are automatically registered when the module is imported.

## Configuration

Server configuration is centralized in `mcp_server.py`:

```python
mcp = FastMCP("lms")
mcp.settings.stateless_http = True  # No session ID required
mcp.settings.json_response = True   # JSON responses (not SSE)
```

To change configuration, modify `mcp_server.py` only.

## Testing

Each module can be tested independently:

- **mcp_server.py**: Test server initialization and configuration
- **lms_mcp_tools.py**: Test individual tool functions
- **mcp_helpers.py**: Test utility functions
- **main.py**: Test server startup

## References

- [FastMCP Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://modelcontextprotocol.io)
- [FastMCP Quickstart Example](https://github.com/modelcontextprotocol/quickstart-resources/blob/main/weather-server-python/weather.py)

# HRB Employee LMS - Python MCP Server

Python-based MCP server providing the same functionality as the Java `hrb_lms` service.

## Features

- **MCP Protocol**: Exposes tools via JSON-RPC 2.0 endpoint (`POST /api/hrb/emp/lms/mcp`)
- **No REST APIs**: Only MCP Protocol endpoint (no REST endpoints exposed)
- **Same Functionality**: Implements the same 6 tools as Java service:
  - `get_leave_balance`
  - `submit_leave_request`
  - `get_leave_history`
  - `get_pending_approvals`
  - `create_hitl_request`
  - `get_hitl_status`

## Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. **Run the server**:
```bash
python main.py
```

The server will start on port 8081 (configurable via `SERVER_PORT`).

## MCP Endpoint

- **URL**: `POST /api/hrb/emp/lms/mcp`
- **Authentication**: `X-API-Key` header
- **Protocol**: JSON-RPC 2.0

### Example Request (tools/list):
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/list",
  "params": {}
}
```

### Example Request (tools/call):
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/call",
  "params": {
    "name": "get_leave_balance",
    "arguments": {
      "employee_id": "EMP001",
      "year": 2025
    }
  }
}
```

## Testing

Run the test scripts:
```bash
python tests/test_all_tools.py
```

## Architecture

- **FastAPI**: Web framework
- **SQLAlchemy**: ORM for database access
- **PostgreSQL**: Database (same as Java service)
- **MCP Protocol**: JSON-RPC 2.0 for tool communication


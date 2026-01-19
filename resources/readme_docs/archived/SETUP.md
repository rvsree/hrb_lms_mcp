# HRB Employee LMS - Python MCP Server Setup Guide

## Overview

`hrb_emp_lms` is a Python-based MCP server that provides the same functionality as the Java `hrb_lms` service. It exposes MCP tools via JSON-RPC 2.0 protocol.

## Features

- **6 MCP Tools** (same as Java service):
  - `get_leave_balance`
  - `submit_leave_request`
  - `get_leave_history`
  - `get_pending_approvals`
  - `create_hitl_request`
  - `get_hitl_status`

- **MCP Protocol**: JSON-RPC 2.0 endpoint at `POST /api/hrb/lms/mcp`
- **No REST APIs**: Only MCP Protocol endpoint (no REST endpoints exposed)
- **Same Database**: Uses the same PostgreSQL database as Java service

## Setup

### 1. Install Dependencies

```bash
cd C:\workspace\poc\MCP\hrb_emp_lms
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file (or copy from `.env.example`):

```bash
# Database Configuration
POSTGRES_DB_HOST=localhost
POSTGRES_DB_PORT=5432
POSTGRES_DB_NAME=coco
POSTGRES_DB_USER=postgres
POSTGRES_DB_PASSWORD=Igates_71

# Server Configuration
SERVER_PORT=8081
API_KEY=default-api-key

# Logging
LOG_LEVEL=INFO
```

### 3. Run the Server

```bash
python main.py
```

The server will start on port 8081 (configurable via `SERVER_PORT`).

## Testing

Run the test script:

```bash
python tests/test_all_tools.py
```

This will test all 6 MCP tools.

## Integration with hrb_copilot

### Configuration

In `hrb_copilot/app-config.yml`:

```yaml
mcp:
  # Enable/Disable MCP Servers
  enable_java_server: "${ENABLE_JAVA_MCP_SERVER:true}"
  enable_python_server: "${ENABLE_PYTHON_MCP_SERVER:false}"
  
  # Python Service Integration
  python_service:
    base_url: "${PYTHON_LEAVE_SERVICE_URL:http://localhost:8081}"
    api_key: "${PYTHON_LEAVE_SERVICE_API_KEY:default-api-key}"
    timeout: 30
```

### Environment Variables

Add to `hrb_copilot/.env`:

```bash
# Enable Python MCP Server
ENABLE_PYTHON_MCP_SERVER=true

# Python Service Configuration
PYTHON_LEAVE_SERVICE_URL=http://localhost:8081
PYTHON_LEAVE_SERVICE_API_KEY=default-api-key
```

### Server Registration

The Python server is automatically registered in `hrb_copilot` on startup if:
1. `enable_python_server` is `true`
2. The server is reachable at the configured URL
3. The MCP Protocol endpoint returns tools

## Architecture

- **FastAPI**: Web framework
- **SQLAlchemy**: ORM for database access
- **PostgreSQL**: Database (same as Java service)
- **MCP Protocol**: JSON-RPC 2.0 for tool communication

## Differences from Java Service

1. **Language**: Python vs Java
2. **Framework**: FastAPI vs Spring Boot
3. **Port**: 8081 (default) vs 8080
4. **Endpoint Path**: Same (`/api/hrb/lms/mcp`) for compatibility

## Troubleshooting

### Server not starting
- Check database connection settings in `.env`
- Ensure PostgreSQL is running
- Check port 8081 is not in use

### Tools not available in hrb_copilot
- Verify `ENABLE_PYTHON_MCP_SERVER=true` in `hrb_copilot/.env`
- Check Python server is running
- Verify `PYTHON_LEAVE_SERVICE_URL` is correct
- Check logs for registration errors

### Database errors
- Ensure database schema matches Java service
- Run `database-setup.sql` from Java service if needed
- Check database credentials


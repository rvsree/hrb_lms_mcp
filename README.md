# HRB Leave Management System MCP Server (hrb_lms_mcp)

**Version:** 1.0  
**Status:** Production  
**Technology Stack:** Python FastMCP, PostgreSQL, MCP Protocol (JSON-RPC 2.0 over HTTP)

---

## Table of Contents

1. [Business Context](#business-context)
2. [Architecture](#architecture)
3. [Environments](#environments)
4. [Setup & Run](#setup--run)
5. [MCP Protocol Implementation](#mcp-protocol-implementation)
6. [Ownership & Operations](#ownership--operations)
7. [First Tasks Checklist](#first-tasks-checklist)
8. [Cross-Project Dependencies](#cross-project-dependencies)

---

## Business Context

### Problem Statement

The HRB Employee Assistant (`hrb_emp_assist`) needs access to real-time operational data (leave balances, leave history, pending approvals) that resides in backend systems. This data cannot be retrieved from policy documents (RAG) and requires direct integration with leave management systems.

### Target Users

- **Primary**: `hrb_emp_assist` application (MCP client)
- **Secondary**: Direct API consumers (if exposed)
- **Administrators**: System administrators managing the MCP server

### Core Workflows

1. **Leave Balance Queries**
   - Retrieve current leave balance for employee
   - Support multiple leave types (PTO, sick, FMLA, etc.)
   - Return real-time data from database

2. **Leave History Queries**
   - Retrieve historical leave requests
   - Filter by date range, leave type, status
   - Support pagination for large result sets

3. **Leave Request Submission**
   - Submit new leave requests
   - Validate leave eligibility
   - Initiate approval workflow

4. **Approval Management**
   - Check pending approvals for managers
   - Retrieve approval status for employees
   - Support approval/rejection actions

5. **HITL (Human-in-the-Loop) Requests**
   - Create escalation requests for complex scenarios
   - Track HITL request status
   - Support polling for completion

### Success Criteria

- **Availability**: >99.9% uptime
- **Response Time**: <500ms for simple queries, <2s for complex queries
- **MCP Protocol Compliance**: 100% JSON-RPC 2.0 compliance
- **Error Rate**: <0.1% error rate
- **Concurrent Requests**: Support 100+ concurrent MCP tool calls

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Client (hrb_emp_assist)              │
│  - Python FastAPI Application                               │
│  - MCP Client Implementation                                │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP (JSON-RPC 2.0)
                       │ POST /mcp (FastMCP streamable-http)
┌──────────────────────▼──────────────────────────────────────┐
│              MCP Server (hrb_lms_mcp)                       │
│  - Python FastMCP Server (Pure FastMCP)                     │
│  - FastMCP streamable-http transport                        │
│  - MCP Tools (@mcp.tool() decorator)                        │
│  - Tool Execution Engine                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌───▼──────────┐
│  PostgreSQL  │ │  Business   │ │  External    │
│  Database    │ │  Logic      │ │  Services    │
│  (Leave Data)│ │  Layer      │ │  (if any)    │
└──────────────┘ └─────────────┘ └──────────────┘
```

### Key Components

1. **FastMCP Server** (`/mcp` - streamable-http endpoint)
   - Pure FastMCP implementation (no FastAPI wrapper)
   - Handles JSON-RPC 2.0 protocol automatically
   - Stateless HTTP mode (no session ID required)
   - JSON responses (not SSE streams)

2. **MCP Tools** (`src/app/api/controller/lms_mcp_tools.py`)
   - All tools registered via `@mcp.tool()` decorator
   - `get_leave_balance`: Query leave balance from database
   - `get_leave_history`: Retrieve leave request history
   - `submit_leave_request`: Create new leave request
   - `get_pending_approvals`: Query pending approvals
   - `create_hitl_request`: Create HITL escalation
   - `get_hitl_status`: Get HITL request status

3. **Validation Models** (`src/app/models/`)
   - Separate Pydantic models for each tool
   - Type-safe argument validation
   - Clear error messages

4. **Data Layer**
   - **PostgreSQL**: Leave requests, balances, approvals
   - **SQLAlchemy**: ORM for database access
   - **Repository Pattern**: Data access abstraction

5. **External Services**
   - **Database**: PostgreSQL (RDS in AWS)
   - **Notification Service**: (Optional) For HITL notifications

### Data Flow

1. **MCP Tool Call Flow**:
   ```
   MCP Client → HTTP POST /mcp (JSON-RPC 2.0) → FastMCP Router 
   → @mcp.tool() Decorator → Tool Function → Pydantic Validation 
   → Service Layer → Database Query → Result → JSON-RPC Response → MCP Client
   ```

2. **Leave Balance Query**:
   ```
   get_leave_balance(employee_id, year) → GetLeaveBalanceArgs validation 
   → LeaveBalanceService → SQLAlchemy Query → Database 
   → Leave Balance Data → JSON Response
   ```

3. **Leave Request Submission**:
   ```
   submit_leave_request(args) → SubmitLeaveRequestArgs validation 
   → LeaveRequestService → Business Logic 
   → Database Insert → Approval Workflow Initiation → JSON Response
   ```

### PII and Security Considerations

- **PII Handling**: Employee IDs, leave balances, personal information stored in database
- **Data Encryption**: 
  - In transit: TLS/HTTPS for all API calls
  - At rest: RDS encryption enabled
- **Access Control**: 
  - API key authentication (`X-API-Key` header)
  - Employee ID validation
  - Role-based access (employee vs manager)
- **Audit Logging**: All tool calls logged with correlation IDs
- **Data Retention**: Per company policy and compliance requirements

---

## Environments

### Local Development
- **Purpose**: Local development and testing
- **Database**: Local PostgreSQL or Docker container
- **Port**: 8080
- **Configuration**: `application.yml`, `application-local.yml`
- **Secrets**: Local properties file (not committed)

### Development (AWS)
- **Purpose**: Shared development environment
- **Database**: RDS PostgreSQL (dev instance)
- **Deployment**: ECS Fargate (dev cluster)
- **Configuration**: AWS Parameter Store, Secrets Manager
- **Secrets**: AWS Secrets Manager (`hrb-lms-mcp/dev/*`)

### Staging
- **Purpose**: Pre-production testing
- **Database**: RDS PostgreSQL (staging instance, Multi-AZ)
- **Deployment**: ECS Fargate (staging cluster)
- **Configuration**: AWS Parameter Store, Secrets Manager
- **Secrets**: AWS Secrets Manager (`hrb-lms-mcp/staging/*`)

### Production
- **Purpose**: Live production environment
- **Database**: RDS PostgreSQL (production, Multi-AZ, automated backups)
- **Deployment**: ECS Fargate (production cluster, auto-scaling)
- **Configuration**: AWS Parameter Store, Secrets Manager
- **Secrets**: AWS Secrets Manager (`hrb-lms-mcp/prod/*`), rotated quarterly

### Configuration Differences

| Setting | Local | Dev | Staging | Prod |
|---------|-------|-----|---------|------|
| Log Level | DEBUG | INFO | INFO | WARNING |
| Database | localhost | RDS (t3.small) | RDS (t3.medium) | RDS (t3.large) |
| Port | 8080 | 8080 (ALB) | 8080 (ALB) | 8080 (ALB) |
| API Key | local-key | Dev key | Staging key | Prod key (rotated) |
| Connection Pool | 10 | 20 | 50 | 100 |

---

## Setup & Run

### Prerequisites

- Python 3.9+
- PostgreSQL 15+ (for local development)
- pip (Python package manager)
- Git

### Local Bootstrap

```bash
# 1. Clone repository
cd C:\workspace\poc\2026\hrb_lms_mcp
git clone <repository-url> .

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up database
# Create PostgreSQL database: hr_chatbot (or as configured)
# Run SQL scripts from resources/db_scripts/
psql -d hr_chatbot -f resources/db_scripts/database-setup.sql
psql -d hr_chatbot -f resources/db_scripts/db-script-sample-data.sql

# 5. Configure environment
# Copy .env.example to .env (if exists) or create .env file
# Edit .env with database connection and API key

# 6. Run application
# Option 1: Direct Python
python -m src.app.api.main

# Option 2: Uvicorn (recommended)
uvicorn src.app.api.main:app --host 127.0.0.1 --port 8190 --reload
```

### Configuration Files

- **`.env`**: Environment variables (database, API key, logging)
- **`src/app/common/config/config.py`**: Settings management (Pydantic Settings)

### Tests

```bash
# Run all tests (if test suite exists)
pytest tests/ -v

# Run specific test file
pytest tests/test_mcp_tools.py -v
```

### Run Locally

```bash
# Development mode (with auto-reload)
uvicorn src.app.api.main:app --host 127.0.0.1 --port 8190 --reload

# Production mode
uvicorn src.app.api.main:app --host 0.0.0.0 --port 8190

# With specific port
uvicorn src.app.api.main:app --host 127.0.0.1 --port 8081
```

### Health Checks

```bash
# MCP Protocol endpoint (tools/list)
curl -X POST http://localhost:8190/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-protocol-version: 2024-11-05" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# MCP Tool execution (tools/call)
curl -X POST http://localhost:8190/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -H "Accept: application/json, text/event-stream" \
  -H "mcp-protocol-version: 2024-11-05" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_leave_balance",
      "arguments": {"employee_id": "EMP001", "year": 2026}
    },
    "id": 2
  }'
```

---

## MCP Protocol Implementation

### MCP Protocol Overview

**Protocol**: JSON-RPC 2.0 over HTTP (FastMCP streamable-http transport)

**Endpoint**: `POST /mcp` (FastMCP streamable-http endpoint)

**Authentication**: API key via `X-API-Key` header (optional, configurable)

**Transport**: FastMCP streamable-http (stateless mode, JSON responses)

### Available Tools

1. **`get_leave_balance`**
   - **Description**: Retrieve employee's leave balance for a specific year
   - **Parameters**: `{"employee_id": "string", "year": int (optional, defaults to current year)}`
   - **Returns**: Leave balance by type (PTO, sick, FMLA, etc.) for the specified year
   - **Validation Model**: `GetLeaveBalanceArgs`

2. **`get_leave_history`**
   - **Description**: Retrieve employee's leave request history
   - **Parameters**: `{"employee_id": "string", "year": int (optional), "status": "string" (optional), "limit": int (optional), "offset": int (optional)}`
   - **Returns**: List of leave requests with status, dates, type
   - **Validation Model**: `GetLeaveHistoryArgs`

3. **`submit_leave_request`**
   - **Description**: Submit new leave request
   - **Parameters**: `{"employee_id": "string", "leave_type": "string", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "reason": "string" (optional)}`
   - **Returns**: Request ID and status
   - **Validation Model**: `SubmitLeaveRequestArgs`

4. **`get_pending_approvals`**
   - **Description**: Get pending leave approvals for a manager
   - **Parameters**: `{"manager_id": "string"}`
   - **Returns**: List of pending approval requests
   - **Validation Model**: `GetPendingApprovalsArgs`

5. **`create_hitl_request`**
   - **Description**: Create human-in-the-loop escalation request
   - **Parameters**: `{"request_type": "string", "query": "string", "employee_id": "string" (optional), "related_entity_type": "string" (optional), "related_entity_id": int (optional), "context": dict (optional), "priority": "string" (optional)}`
   - **Returns**: HITL request ID and status
   - **Validation Model**: `CreateHITLRequestArgs`

6. **`get_hitl_status`**
   - **Description**: Get HITL request status
   - **Parameters**: `{"hitl_request_id": int}`
   - **Returns**: HITL request status and details
   - **Validation Model**: `GetHITLStatusArgs`

### Tool Selection Strategy

- Tools are automatically registered via `@mcp.tool()` decorator in `lms_mcp_tools.py`
- FastMCP automatically generates tool schemas from function signatures and docstrings
- Tools are exposed via MCP Protocol `tools/list` method
- MCP client (`hrb_emp_assist`) discovers available tools at runtime
- Tool descriptions guide LLM in tool selection
- Tool execution via `tools/call` method
- All tools use Pydantic validation models for type-safe argument validation

### Error Handling

- **Invalid Parameters**: Returns JSON-RPC error with code -32602
- **Tool Not Found**: Returns JSON-RPC error with code -32601
- **Database Errors**: Returns JSON-RPC error with code -32000
- **Timeout**: 30 seconds default, configurable

### Rate Limits

- **Per Client**: 100 requests/minute per API key
- **Per Tool**: 50 requests/minute per tool per client
- **Backoff**: Exponential backoff on rate limit (429 response)

---

## Ownership & Operations

### Infrastructure Ownership

- **AWS Infrastructure**: DevOps/Platform Team
  - ECS clusters, RDS instances, ALB, VPC, security groups
  - Secrets Manager, Parameter Store
  - CloudWatch logs and metrics

- **Application Code**: Development Team
  - Feature development, bug fixes
  - MCP tool implementations
  - Database schema changes

### Change Management

- **Code Changes**: 
  - Feature branches → PR → Code review → Merge to `main`
  - Automated tests must pass
  - Deployment via GitHub Actions to dev/staging/prod

- **Infrastructure Changes**:
  - Terraform/CDK changes require platform team approval
  - Changes to production require change request

- **Database Changes**:
  - Migration scripts in `src/main/resources/db/migration/`
  - Test migrations in dev/staging before production

### Support & Runbooks

**Entry Points**:
- **Application Issues**: Check CloudWatch logs (`/ecs/hrb-lms-mcp`)
- **Database Issues**: Check RDS metrics, connection pool status
- **MCP Protocol Issues**: Verify JSON-RPC compliance, check request/response logs

**Common Runbooks**:
- **Service Unhealthy**: Check health endpoint, review logs, verify database connectivity
- **High Latency**: Check database query performance, connection pool exhaustion
- **MCP Protocol Errors**: Verify JSON-RPC format, check tool implementations
- **Database Connection Issues**: Check RDS endpoint, security groups, connection pool settings

**On-Call Rotation**: Development team (primary), Platform team (escalation)

---

## First Tasks Checklist

For a new agent/developer joining the project:

### 1. Set Up Local Environment

- [ ] Clone repository: `git clone <repo-url> C:\workspace\poc\2026\hrb_lms_mcp`
- [ ] Install Python 3.9+ and pip
- [ ] Create virtual environment: `python -m venv .venv`
- [ ] Activate virtual environment: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Linux/Mac)
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Set up local PostgreSQL database
- [ ] Create `.env` file with database connection and API key
- [ ] Run database setup scripts: `psql -d hr_chatbot -f resources/db_scripts/database-setup.sql`
- [ ] Load sample data: `psql -d hr_chatbot -f resources/db_scripts/db-script-sample-data.sql`

### 2. Run Tests

- [ ] Run `pytest tests/ -v` - all tests should pass (if test suite exists)
- [ ] Review test output for any failures
- [ ] Run specific test file: `pytest tests/test_mcp_tools.py -v`

### 3. Perform Smoke Test

- [ ] Start application: `uvicorn src.app.api.main:app --host 127.0.0.1 --port 8190 --reload`
- [ ] Test MCP Protocol endpoint (tools/list):
  ```bash
  curl -X POST http://localhost:8190/mcp \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your-api-key" \
    -H "Accept: application/json, text/event-stream" \
    -H "mcp-protocol-version: 2024-11-05" \
    -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
  ```
- [ ] Test tool execution (tools/call):
  ```bash
  curl -X POST http://localhost:8190/mcp \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your-api-key" \
    -H "Accept: application/json, text/event-stream" \
    -H "mcp-protocol-version: 2024-11-05" \
    -d '{
      "jsonrpc": "2.0",
      "method": "tools/call",
      "params": {
        "name": "get_leave_balance",
        "arguments": {"employee_id": "EMP001", "year": 2026}
      },
      "id": 2
    }'
  ```
- [ ] Verify response is returned successfully

### 4. Review Logs and Health Checks

- [ ] Check application logs (console output with colored logging)
- [ ] Verify no errors in startup logs
- [ ] Look for log message: "HRB Employee LMS MCP Server initialized with Pure FastMCP (streamable-http)"
- [ ] Review log structure: `[MCP]` tags for MCP-related logs
- [ ] Verify tool execution logs show correct parameters

### 5. Explore Codebase

- [ ] Review `src/app/api/main.py` - Pure FastMCP server entry point
- [ ] Review `src/app/api/controller/lms_mcp_tools.py` - MCP tools with `@mcp.tool()` decorator
- [ ] Review `src/app/models/` - Pydantic validation models for each tool
- [ ] Review `src/app/services/` - Business logic layer (LeaveBalanceService, LeaveRequestService, HitlService)
- [ ] Review `src/app/repos/` - Data access layer (SQLAlchemy)
- [ ] Review `resources/db_scripts/` - Database setup and sample data scripts
- [ ] Review `tests/` - Test structure and examples (if exists)

---

## Cross-Project Dependencies

### Shared Components

1. **MCP Protocol**: Both projects use MCP (Model Context Protocol) for service communication
   - **Location**: 
     - `hrb_lms_mcp` (C:\workspace\poc\2026\hrb_lms_mcp): Implements MCP server (Python FastMCP) - **THIS PROJECT**
     - `hrb_emp_assist` (C:\workspace\poc\2026\hrb_emp_assist): Implements MCP client (Python)
   - **Interface**: JSON-RPC 2.0 over HTTP (FastMCP streamable-http transport)
   - **Protocol Endpoint**: `/mcp` (FastMCP streamable-http endpoint exposed by this server)
   - **Communication**: `hrb_emp_assist` → HTTP POST `/mcp` → `hrb_lms_mcp` (this server)
   - **Specification**: Follows MCP protocol specification (FastMCP SDK)
   - **Transport**: FastMCP streamable-http (stateless mode, JSON responses)

2. **Common Libraries** (if any):
   - Shared utilities, logging, configuration patterns
   - Location: TBD (may be in separate shared library at `C:\workspace\poc\2026\hrb_shared`)

3. **Infrastructure Modules**:
   - Shared Terraform/CDK modules for common AWS resources
   - Location: TBD (infrastructure repository, e.g., `C:\workspace\poc\2026\hrb_infrastructure`)
   - Shared resources: VPC, security groups, IAM roles, KMS keys

4. **Shared AWS Resources**:
   - **VPC**: `hrb-services-vpc` (shared with `hrb_emp_assist`)
   - **ECS Cluster**: `hrb-services-cluster` (shared)
   - **KMS Keys**: Database encryption, secrets encryption (shared)
   - **CloudWatch Log Groups**: Separate per project but same retention policies

### Versioning & Release Conventions

**Semantic Versioning**: `MAJOR.MINOR.PATCH`
- **MAJOR**: Breaking changes to MCP protocol or API
- **MINOR**: New tools, backward compatible changes
- **PATCH**: Bug fixes, backward compatible

**Branch Strategy**:
- **`main`**: Production-ready code
- **`develop`**: Integration branch for features
- **`feature/*`**: Feature development branches
- **`hotfix/*`**: Production hotfixes

**Tag Strategy**:
- **Release tags**: `v1.0.0`, `v1.1.0`, etc.
- **Pre-release tags**: `v1.1.0-rc1`, `v1.1.0-beta1`

**Release Process**:
1. Feature development in `feature/*` branches
2. Merge to `develop` after code review
3. Create release branch from `develop`
4. Tag release: `v1.1.0`
5. Merge to `main` and deploy to production

**MCP Protocol Versioning**:
- MCP protocol version: 1.0 (current)
- Tool versioning: Tools are versioned independently
- Breaking changes: Require MAJOR version bump

**Cross-Project Coordination**:
- **MCP Protocol Changes**: Require coordination with `hrb_emp_assist` (MCP client)
- **Breaking Changes**: MCP protocol changes require MAJOR version bump in both projects
- **Deployment Order**: Deploy `hrb_lms_mcp` first (Phase 0), then `hrb_emp_assist` (Phase 1-8)
- **API Compatibility**: Maintain backward compatibility for at least 2 minor versions

---

## Additional Resources

- **MCP Protocol Specification**: `docs/MCP-PROTOCOL.md`
- **API Documentation**: `docs/api/`
- **Deployment Guide**: `resources/aws_platforming/readme-aws-platforming.md`
- **Database Schema**: `docs/database-schema.md`
- **Tool Documentation**: `docs/tools/`

---

**Last Updated**: 2026-01-24  
**Maintained By**: Development Team  
**Questions**: Contact team lead or create issue in repository

---

## FastMCP Implementation Details

### Pure FastMCP Architecture

This project uses **Pure FastMCP** (no FastAPI wrapper):

- **Entry Point**: `src/app/api/main.py` uses `mcp.streamable_http_app()` directly
- **Tool Registration**: All tools use `@mcp.tool()` decorator in `lms_mcp_tools.py`
- **Transport**: FastMCP streamable-http (stateless mode, JSON responses)
- **Protocol**: JSON-RPC 2.0 handled automatically by FastMCP

### Key Files

- `src/app/api/main.py`: FastMCP server initialization and middleware
- `src/app/api/controller/lms_mcp_tools.py`: All MCP tool implementations
- `src/app/models/*_args.py`: Pydantic validation models for each tool
- `src/app/services/`: Business logic layer
- `src/app/repos/`: Database access layer

### Dependencies

- `mcp>=1.2.0`: FastMCP SDK
- `uvicorn[standard]>=0.24.0`: ASGI server
- `sqlalchemy>=2.0.23`: ORM
- `pydantic>=2.5.0`: Validation
- `psycopg2-binary>=2.9.9`: PostgreSQL driver

**Note**: FastAPI and Starlette are NOT required for FastMCP (FastMCP uses Starlette internally).

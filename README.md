# HRB Leave Management System MCP Server (hrb_lms_mcp)

**Version:** 1.0  
**Status:** Production  
**Technology Stack:** Java Spring Boot, PostgreSQL, MCP Protocol (JSON-RPC 2.0)

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
                       │ HTTP/REST (JSON-RPC 2.0)
                       │ POST /api/hrb/lms/mcp
┌──────────────────────▼──────────────────────────────────────┐
│              MCP Server (hrb_lms_mcp)                       │
│  - Java Spring Boot Application                             │
│  - MCP Protocol Handler                                     │
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

1. **MCP Protocol Handler** (`/api/hrb/lms/mcp`)
   - Receives JSON-RPC 2.0 requests
   - Routes to appropriate tool handlers
   - Returns JSON-RPC 2.0 responses

2. **Tool Implementations**
   - `get_leave_balance`: Query leave balance from database
   - `get_leave_history`: Retrieve leave request history
   - `submit_leave_request`: Create new leave request
   - `check_pending_approvals`: Query pending approvals
   - `create_hitl_request`: Create HITL escalation

3. **Data Layer**
   - **PostgreSQL**: Leave requests, balances, approvals
   - **JPA/Hibernate**: ORM for database access
   - **Repository Pattern**: Data access abstraction

4. **External Services**
   - **Database**: PostgreSQL (RDS in AWS)
   - **Notification Service**: (Optional) For HITL notifications

### Data Flow

1. **MCP Tool Call Flow**:
   ```
   MCP Client → HTTP POST /api/hrb/lms/mcp → JSON-RPC Handler 
   → Tool Router → Tool Implementation → Database Query 
   → Result → JSON-RPC Response → MCP Client
   ```

2. **Leave Balance Query**:
   ```
   get_leave_balance(employee_id) → Repository → Database 
   → Leave Balance Entity → DTO → JSON Response
   ```

3. **Leave Request Submission**:
   ```
   submit_leave_request(args) → Validation → Business Logic 
   → Database Insert → Approval Workflow Initiation → Response
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

- Java 17+
- Maven 3.9+
- PostgreSQL 15+ (for local development)
- Docker Desktop (optional, for containerized local setup)
- Git

### Local Bootstrap

```bash
# 1. Clone repository
cd C:\workspace\poc\2026\hrb_lms_mcp
git clone <repository-url> .

# 2. Build project
mvn clean install

# 3. Set up database
# Create PostgreSQL database: leave_management_db
# Run migration scripts from src/main/resources/db/migration/

# 4. Configure application
cp src/main/resources/application-local.yml.example src/main/resources/application-local.yml
# Edit application-local.yml with database connection and API key

# 5. Run application
mvn spring-boot:run

# Or with specific profile
mvn spring-boot:run -Dspring-boot.run.profiles=local
```

### Configuration Files

- **`application.yml`**: Base configuration
- **`application-local.yml`**: Local development overrides
- **`application-dev.yml`**: Development environment
- **`application-staging.yml`**: Staging environment
- **`application-prod.yml`**: Production environment

### Tests

```bash
# Run all tests
mvn test

# Run unit tests only
mvn test -Dtest=*Test

# Run integration tests
mvn verify -Dtest=*IT

# Run with coverage
mvn test jacoco:report
```

### Linting

```bash
# Format code (if using Spotless)
mvn spotless:apply

# Check code style
mvn checkstyle:check

# Static analysis
mvn pmd:check
```

### Run Locally

```bash
# Development mode (with auto-reload)
mvn spring-boot:run -Dspring-boot.run.profiles=local

# Production mode
java -jar target/hrb-lms-mcp-1.0.0.jar --spring.profiles.active=local

# With specific port
mvn spring-boot:run -Dspring-boot.run.arguments=--server.port=8080
```

### Health Checks

```bash
# Application health (Spring Boot Actuator)
curl http://localhost:8080/actuator/health

# MCP Protocol endpoint
curl -X POST http://localhost:8080/api/hrb/lms/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

---

## MCP Protocol Implementation

### MCP Protocol Overview

**Protocol**: JSON-RPC 2.0 over HTTP/REST

**Endpoint**: `POST /api/hrb/lms/mcp`

**Authentication**: API key via `X-API-Key` header

### Available Tools

1. **`get_leave_balance`**
   - **Description**: Retrieve employee's current leave balance
   - **Parameters**: `{"employee_id": "string"}`
   - **Returns**: Leave balance by type (PTO, sick, FMLA, etc.)

2. **`get_leave_history`**
   - **Description**: Retrieve employee's leave request history
   - **Parameters**: `{"employee_id": "string", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}`
   - **Returns**: List of leave requests with status, dates, type

3. **`submit_leave_request`**
   - **Description**: Submit new leave request
   - **Parameters**: `{"employee_id": "string", "leave_type": "string", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "reason": "string"}`
   - **Returns**: Request ID and status

4. **`check_pending_approvals`**
   - **Description**: Check pending leave approvals for manager
   - **Parameters**: `{"employee_id": "string"}` (manager's employee_id)
   - **Returns**: List of pending approval requests

5. **`create_hitl_request`**
   - **Description**: Create human-in-the-loop escalation request
   - **Parameters**: `{"request_type": "string", "query": "string", "employee_id": "string"}`
   - **Returns**: HITL request ID and status

### Tool Selection Strategy

- Tools are exposed via MCP Protocol `tools/list` method
- MCP client (`hrb_emp_assist`) discovers available tools at runtime
- Tool descriptions guide LLM in tool selection
- Tool execution via `tools/call` method

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
- [ ] Install Java 17+ and Maven 3.9+
- [ ] Set up local PostgreSQL database
- [ ] Run `mvn clean install` to build project
- [ ] Copy `application-local.yml.example` to `application-local.yml`
- [ ] Configure database connection and API key in `application-local.yml`
- [ ] Run database migrations: `mvn flyway:migrate` (if using Flyway)

### 2. Run Tests

- [ ] Run `mvn test` - all tests should pass
- [ ] Review test output for any failures
- [ ] Run `mvn test -Dtest=*Test` - unit tests
- [ ] Run `mvn verify -Dtest=*IT` - integration tests

### 3. Perform Smoke Test

- [ ] Start application: `mvn spring-boot:run -Dspring-boot.run.profiles=local`
- [ ] Test health endpoint: `curl http://localhost:8080/actuator/health`
- [ ] Test MCP Protocol endpoint:
  ```bash
  curl -X POST http://localhost:8080/api/hrb/lms/mcp \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your-api-key" \
    -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
  ```
- [ ] Test tool execution:
  ```bash
  curl -X POST http://localhost:8080/api/hrb/lms/mcp \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your-api-key" \
    -d '{
      "jsonrpc": "2.0",
      "method": "tools/call",
      "params": {
        "name": "get_leave_balance",
        "arguments": {"employee_id": "EMP001"}
      },
      "id": 2
    }'
  ```
- [ ] Verify response is returned successfully

### 4. Review Logs and Health Checks

- [ ] Check application logs (console output or log files)
- [ ] Verify no errors in startup logs
- [ ] Test health endpoints:
  - [ ] `/actuator/health` - application health
  - [ ] `/actuator/health/db` - database connectivity (if configured)
- [ ] Review log structure and correlation IDs

### 5. Explore Codebase

- [ ] Review `src/main/java/.../mcp/` - MCP protocol handler
- [ ] Review `src/main/java/.../tools/` - tool implementations
- [ ] Review `src/main/java/.../repository/` - data access layer
- [ ] Review `src/main/resources/db/migration/` - database migrations
- [ ] Review `src/test/` - test structure and examples

---

## Cross-Project Dependencies

### Shared Components

1. **MCP Protocol**: Both projects use MCP (Model Context Protocol) for service communication
   - **Location**: 
     - `hrb_lms_mcp` (C:\workspace\poc\2026\hrb_lms_mcp): Implements MCP server (Java Spring Boot) - **THIS PROJECT**
     - `hrb_emp_assist` (C:\workspace\poc\2026\hrb_emp_assist): Implements MCP client (Python)
   - **Interface**: JSON-RPC 2.0 over HTTP/REST
   - **Protocol Endpoint**: `/api/hrb/lms/mcp` (exposed by this server)
   - **Communication**: `hrb_emp_assist` → HTTP POST → `hrb_lms_mcp` (this server)
   - **Specification**: Follows MCP protocol specification

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

**Last Updated**: 2026-01-18  
**Maintained By**: Development Team  
**Questions**: Contact team lead or create issue in repository

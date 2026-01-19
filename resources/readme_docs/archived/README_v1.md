# HRB LMS (HR Benefits Leave Management Service)

## 🎯 Overview

Spring Boot microservice for managing employee leave requests, balances, and approvals. Provides REST APIs for leave management operations with API key authentication.

## 📋 Features

- ✅ Check leave balance
- ✅ Submit leave requests
- ✅ Get leave history
- ✅ Get pending approvals (for managers)
- ✅ Approve/Reject leave requests
- ✅ Human-in-the-Loop (HITL) request management

## 🚀 Quick Start

### Prerequisites
- Java 17+
- Maven 3.8+
- PostgreSQL 15+ (Aurora PostgreSQL, RDS, or local)

### Database Setup

1. **Create Database**: Create a PostgreSQL database (default name: `coco`)

2. **Run Database Script**: Execute `database-setup.sql` in your PostgreSQL database
   ```sql
   -- This script creates all tables and inserts sample data
   -- Run in your PostgreSQL client (pgAdmin, DBeaver, psql, etc.)
   ```

3. **Verify Data**: After running the script, verify:
   - 5 managers (MGR001-MGR005)
   - 50 employees (EMP001-EMP050)
   - 6 leave types (PTO, SICK, UNPAID, etc.)
   - Leave balances for all employees
   - Sample leave requests

### Configuration

The application connects to PostgreSQL using environment variables or `application.yml`:

```bash
# Environment Variables (optional)
POSTGRES_DB_HOST=localhost          # or your Aurora endpoint
POSTGRES_DB_PORT=5432
POSTGRES_DB_NAME=coco
POSTGRES_DB_USER=postgres
POSTGRES_DB_PASSWORD=<your-password>
API_KEY=default-api-key              # Your API key for authentication
```

Or update defaults in `src/main/resources/application.yml`

### Run Application

**From IntelliJ IDEA:**
1. Right-click `HrbLmsApplication.java` → Run
2. Or use the run configuration

**From Command Line:**
```bash
mvn spring-boot:run
```

### Access APIs

- **Base URL**: http://localhost:8080
- **Swagger UI**: http://localhost:8080/swagger-ui.html
- **API Docs**: http://localhost:8080/api-docs
- **Health Check**: http://localhost:8080/actuator/health

## 📡 API Endpoints

All endpoints require API key authentication via `X-API-Key` header (except Swagger UI and Actuator).

### Leave Balance
- `GET /api/v1/leave/balance/{employee_id}` - Get leave balance for an employee

### Leave Requests
- `POST /api/v1/leave/requests` - Submit a new leave request
- `GET /api/v1/leave/requests` - Get leave history (with optional filters)
- `GET /api/v1/leave/requests/{id}` - Get specific leave request

### Approvals
- `GET /api/v1/leave/approvals/pending` - Get pending approvals for a manager
- `POST /api/v1/leave/requests/{id}/approve` - Approve a leave request
- `POST /api/v1/leave/requests/{id}/reject` - Reject a leave request

### HITL Requests
- `POST /api/v1/hitl/requests` - Create a HITL request
- `GET /api/v1/hitl/requests/{id}` - Get HITL request status
- `POST /api/v1/hitl/requests/{id}/respond` - Respond to a HITL request

## 🔐 Security

- **Authentication**: API Key via `X-API-Key` header
- **Default API Key**: `default-api-key` (configure in `application.yml` or environment variable)
- **Public Endpoints**: Swagger UI, API docs, Actuator endpoints
- **Protected Endpoints**: All `/api/v1/**` endpoints require valid API key

### Using API Key

**In Postman/HTTP Client:**
```
Header: X-API-Key: default-api-key
```

**In Swagger UI:**
1. Click "Authorize" button (lock icon)
2. Enter API key value
3. Click "Authorize"

## 🗄️ Database Schema

The database includes:
- **employees**: Employee information with manager relationships
- **leave_types**: Types of leave (PTO, SICK, etc.)
- **leave_balances**: Employee leave balances by year
- **leave_requests**: Leave request records
- **hitl_requests**: Human-in-the-loop escalation requests

See `database-setup.sql` for complete schema and sample data.

## 📚 Documentation

- **API Documentation**: Swagger UI at http://localhost:8080/swagger-ui.html
- **Postman Collection**: `Leave-Management-Service.postman_collection.json`
- **Database Setup**: `database-setup.sql`

## 🧪 Testing

1. **Swagger UI**: Interactive API testing at http://localhost:8080/swagger-ui.html
2. **Postman**: Import `Leave-Management-Service.postman_collection.json`
3. **Health Check**: http://localhost:8080/actuator/health

## 📝 Notes

- Database is manually managed (no Flyway migrations)
- Sample data includes 50 employees across 5 departments
- All endpoints return JSON responses
- Error handling with standardized error responses


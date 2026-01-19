# HR_CHATBOT Database Setup - Complete Guide

**Date**: 2025-01-10  
**Database**: `hr_chatbot` (PostgreSQL)  
**Schemas**: `hrb_emp_lms`, `public`

---

## Overview

This guide explains how to set up the `hr_chatbot` database with all required tables for both:
- **hrb_emp_lms** (Leave Management Service) - in `hrb_emp_lms` schema
- **hrb_copilot** (HR Benefits Chatbot) - in `public` schema

---

## Database Configuration

Update your `.env` file with these settings:

```env
POSTGRES_DB_HOST=localhost
POSTGRES_DB_PORT=5432
POSTGRES_DB_NAME=hr_chatbot
POSTGRES_DB_USER=postgres
POSTGRES_DB_PASSWORD=Igates_71
```

---

## Setup Steps

### Step 1: Create Database

First, ensure the `hr_chatbot` database exists:

```bash
psql -U postgres -c "CREATE DATABASE hr_chatbot;"
```

### Step 2: Run hrb_emp_lms Schema Setup

Run the updated `database-setup.sql` script to create the `hrb_emp_lms` schema:

```bash
cd c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f database-setup.sql
```

**This creates**:
- Schema: `hrb_emp_lms`
- Tables: `employees`, `leave_types`, `leave_balances`, `leave_requests`, `hitl_requests`
- Sample data including test employees: `emp_12345`, `emp_67890`, `emp_11111`

### Step 3: Run hrb_copilot Schema Setup

Run the hrb_copilot schema files (these should be in your hrb_copilot project):

```bash
# Navigate to hrb_copilot project
cd c:\workspace\poc\chatbot\agentic_ai

# Run required tables (chat_sessions, chat_history, user_feedback)
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/hr_chatbot_schema.sql
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/hr_chatbot_schema_dml.sql

# Run optional tables (policy_versions, leave_rules, agent_tasks)
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/coco_schema_extensions.sql
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/coco_schema_dml.sql
```

**This creates** (in `public` schema):
- Required tables: `chat_sessions`, `chat_history`, `user_feedback`
- Optional tables: `policy_versions`, `leave_rules`, `agent_tasks`

### Step 4: Verify Setup

Run the verification script:

```bash
cd c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f verify_hr_chatbot_database.sql
```

Or run the Python test script:

```bash
cd c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts
python test_hr_chatbot_endpoints.py
```

---

## Required Tables

### hrb_emp_lms Schema (5 tables)

| Table | Purpose | Required |
|-------|---------|----------|
| `employees` | Employee master data | ✅ Required |
| `leave_types` | Leave type definitions (PTO, SICK, etc.) | ✅ Required |
| `leave_balances` | Employee leave balances | ✅ Required |
| `leave_requests` | Leave request records | ✅ Required |
| `hitl_requests` | Human-in-the-loop requests | ✅ Required |

**Test Employees Included**: `emp_12345`, `emp_67890`, `emp_11111`

### public Schema - Required (3 tables)

| Table | Purpose | Required |
|-------|---------|----------|
| `chat_sessions` | Chat session tracking | ✅ Required |
| `chat_history` | Chat message history | ✅ Required |
| `user_feedback` | User feedback collection | ✅ Required |

### public Schema - Optional (3 tables)

| Table | Purpose | Required |
|-------|---------|----------|
| `policy_versions` | Policy document versioning | ⚠️ Optional |
| `leave_rules` | Structured leave rules | ⚠️ Optional |
| `agent_tasks` | Agent task tracking | ⚠️ Optional |

**Note**: Optional tables are from `coco_schema_extensions.sql`. They are useful for advanced features but not required for basic functionality.

---

## What's Missing?

### If Verification Fails

Check the verification output to see what's missing:

1. **Missing hrb_emp_lms schema/tables**:
   - ✅ **Solution**: Run `database-setup.sql` (Step 2)

2. **Missing chat_sessions, chat_history, user_feedback**:
   - ✅ **Solution**: Run `hr_chatbot_schema.sql` and `hr_chatbot_schema_dml.sql` (Step 3)

3. **Missing policy_versions, leave_rules, agent_tasks**:
   - ⚠️ **Solution**: Run `coco_schema_extensions.sql` and `coco_schema_dml.sql` (Step 3 - optional)
   - These are optional - only run if you need advanced policy versioning and rule tracking

4. **Missing test employees (emp_12345, emp_67890, emp_11111)**:
   - ✅ **Solution**: The `database-setup.sql` script includes these employees. If missing, they may not have been inserted. Check the script output for errors.

---

## Sample Data

### hrb_emp_lms Schema

- **55 employees** (5 managers + 50 employees, including 3 test employees)
- **6 leave types** (PTO, SICK, UNPAID, SABBATICAL, MATERNITY, PATERNITY)
- **Leave balances** for all employees (2025)
- **Sample leave requests** (approved, pending, rejected, pending_hitl)
- **Sample HITL request**

### hrb_copilot Schema (from hr_chatbot_schema_dml.sql)

- **3 sample chat sessions** (session_001, session_002, session_003)
- **Sample chat history** with reasoning traces
- **Sample user feedback**

---

## Testing

### Test Database Connection

```bash
psql -h localhost -p 5432 -U postgres -d hr_chatbot -c "SELECT version();"
```

### Test hrb_emp_lms Schema

```sql
-- Check test employees exist
SELECT employee_id, name, email 
FROM hrb_emp_lms.employees 
WHERE employee_id IN ('emp_12345', 'emp_67890', 'emp_11111');

-- Check leave balances
SELECT e.employee_id, lt.code, lb.accrued, lb.used, lb.available
FROM hrb_emp_lms.employees e
JOIN hrb_emp_lms.leave_balances lb ON lb.employee_id = e.id
JOIN hrb_emp_lms.leave_types lt ON lt.id = lb.leave_type_id
WHERE e.employee_id = 'emp_12345';
```

### Test Chat Endpoint

Use the Python test script:

```bash
python test_hr_chatbot_endpoints.py
```

Or manually test with curl:

```bash
curl -X POST http://127.0.0.1:8181/hrb/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is my leave balance?",
    "session_id": "test_001",
    "user_context": {
      "employee_id": "emp_12345"
    },
    "options": {
      "enable_mcp": true
    }
  }'
```

---

## Troubleshooting

### Error: "schema hrb_emp_lms does not exist"

**Solution**: Run `database-setup.sql` which creates the schema.

### Error: "relation hrb_emp_lms.employees does not exist"

**Solution**: The tables weren't created. Check the SQL script output for errors. Make sure you have CREATE TABLE privileges.

### Error: "Employee not found with ID: emp_12345"

**Solution**: The test employees weren't inserted. Check the INSERT statements in `database-setup.sql` for errors. Verify managers were inserted first.

### Error: "relation chat_sessions does not exist"

**Solution**: Run `hr_chatbot_schema.sql` to create the hrb_copilot tables.

### API Connection Errors

**Solution**: Make sure the hrb_copilot API server is running:
```bash
cd c:\workspace\poc\dec_2025\hrb_copilot
uvicorn src.app.api.main:app --reload --port 8181
```

---

## File Locations

### hrb_emp_lms Scripts

- `c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts\database-setup.sql`
- `c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts\setup_hr_chatbot_master.sql`
- `c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts\verify_hr_chatbot_database.sql`
- `c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts\test_hr_chatbot_endpoints.py`
- `c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts\README_DATABASE_SETUP.md` (this file)

### hrb_copilot Scripts

- `c:\workspace\poc\chatbot\agentic_ai\src\app\common\db_scripts\postgres\hr_chatbot_schema.sql`
- `c:\workspace\poc\chatbot\agentic_ai\src\app\common\db_scripts\postgres\hr_chatbot_schema_dml.sql`
- `c:\workspace\poc\chatbot\agentic_ai\src\app\common\db_scripts\postgres\coco_schema_extensions.sql`
- `c:\workspace\poc\chatbot\agentic_ai\src\app\common\db_scripts\postgres\coco_schema_dml.sql`

---

## Quick Reference

### Complete Setup (All Steps)

```bash
# Step 1: Create database (if not exists)
psql -U postgres -c "CREATE DATABASE hr_chatbot;"

# Step 2: Setup hrb_emp_lms schema
cd c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f database-setup.sql

# Step 3: Setup hrb_copilot tables
cd c:\workspace\poc\chatbot\agentic_ai
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/hr_chatbot_schema.sql
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/hr_chatbot_schema_dml.sql
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/coco_schema_extensions.sql
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/coco_schema_dml.sql

# Step 4: Verify
cd c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts
psql -h localhost -p 5432 -U postgres -d hr_chatbot -f verify_hr_chatbot_database.sql
python test_hr_chatbot_endpoints.py
```

---

**Last Updated**: 2025-01-10  
**Status**: ✅ Ready for use






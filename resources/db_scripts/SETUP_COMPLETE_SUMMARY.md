# Database Setup - Summary and Manual Execution Instructions

**Date**: 2025-01-11  
**Status**: ✅ All SQL scripts prepared and ready for execution

---

## ✅ What Was Completed

1. **Updated `database-setup.sql`**:
   - All tables now use `hrb_emp_lms` schema prefix
   - Schema creation included
   - Test employees added: `emp_12345`, `emp_67890`, `emp_11111`
   - All references updated

2. **Created Verification Scripts**:
   - `verify_hr_chatbot_database.sql` - SQL verification
   - `test_hr_chatbot_endpoints.py` - Python endpoint testing

3. **Created Documentation**:
   - `README_DATABASE_SETUP.md` - Complete setup guide
   - `setup_hr_chatbot_master.sql` - Master setup script (optional)

---

## ⚠️ Note: psql Not in PATH

The `psql` command is not available in the current PowerShell session. You'll need to either:

**Option 1**: Add PostgreSQL bin directory to PATH, or  
**Option 2**: Use full path to psql.exe, or  
**Option 3**: Use pgAdmin or another PostgreSQL client

---

## 📋 Manual Execution Steps

### Step 1: Find psql Location

Common PostgreSQL installation paths on Windows:
- `C:\Program Files\PostgreSQL\15\bin\psql.exe` (or version 14, 16, etc.)
- `C:\Program Files (x86)\PostgreSQL\15\bin\psql.exe`

### Step 2: Run hrb_emp_lms Schema Setup

```powershell
# Navigate to the scripts directory
cd c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts

# Run the schema setup (replace path to psql if needed)
$env:PGPASSWORD='Igates_71'
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d hr_chatbot -f database-setup.sql
```

### Step 3: Run hrb_copilot Schema Setup

```powershell
# Navigate to hrb_copilot project
cd c:\workspace\poc\chatbot\agentic_ai

# Run required schema files
$env:PGPASSWORD='Igates_71'
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/hr_chatbot_schema.sql
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/hr_chatbot_schema_dml.sql

# Run optional schema files
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/coco_schema_extensions.sql
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d hr_chatbot -f src/app/common/db_scripts/postgres/coco_schema_dml.sql
```

### Step 4: Verify Setup

```powershell
# Navigate back to scripts directory
cd c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts

# Run verification
$env:PGPASSWORD='Igates_71'
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h localhost -p 5432 -U postgres -d hr_chatbot -f verify_hr_chatbot_database.sql
```

### Step 5: Test Endpoints (Optional)

```powershell
# Install required packages if needed
pip install httpx psycopg2-binary

# Run Python test script
python test_hr_chatbot_endpoints.py
```

---

## 🔍 Quick Verification Queries

You can also verify manually using these SQL queries:

```sql
-- Check hrb_emp_lms schema exists
SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'hrb_emp_lms';

-- Check test employees exist
SELECT employee_id, name, email 
FROM hrb_emp_lms.employees 
WHERE employee_id IN ('emp_12345', 'emp_67890', 'emp_11111');

-- Check table counts
SELECT 
    'hrb_emp_lms.employees' as table_name,
    COUNT(*) as row_count
FROM hrb_emp_lms.employees
UNION ALL
SELECT 'hrb_emp_lms.leave_types', COUNT(*) FROM hrb_emp_lms.leave_types
UNION ALL
SELECT 'hrb_emp_lms.leave_balances', COUNT(*) FROM hrb_emp_lms.leave_balances
UNION ALL
SELECT 'chat_sessions', COUNT(*) FROM chat_sessions
UNION ALL
SELECT 'chat_history', COUNT(*) FROM chat_history
UNION ALL
SELECT 'user_feedback', COUNT(*) FROM user_feedback;
```

---

## 📁 Files Created/Updated

All files in: `c:\workspace\poc\MCP\hrb_emp_lms\resources\db_scripts\`

1. ✅ `database-setup.sql` - Updated with hrb_emp_lms schema
2. ✅ `verify_hr_chatbot_database.sql` - Verification script
3. ✅ `test_hr_chatbot_endpoints.py` - Python test script
4. ✅ `README_DATABASE_SETUP.md` - Complete documentation
5. ✅ `setup_hr_chatbot_master.sql` - Master setup (optional)

---

## ✅ Expected Results

After running all scripts successfully, you should have:

### hrb_emp_lms Schema (5 tables):
- ✅ `employees` - ~58 rows (5 managers + 50 employees + 3 test employees)
- ✅ `leave_types` - 6 rows
- ✅ `leave_balances` - ~116 rows (PTO + SICK for all employees)
- ✅ `leave_requests` - ~10+ rows
- ✅ `hitl_requests` - 1 row

### public Schema (hrb_copilot):
- ✅ `chat_sessions` - 3 rows (from hr_chatbot_schema_dml.sql)
- ✅ `chat_history` - 4+ rows (from hr_chatbot_schema_dml.sql)
- ✅ `user_feedback` - 2 rows (from hr_chatbot_schema_dml.sql)
- ⚠️ `policy_versions` - Optional (from coco_schema_extensions.sql)
- ⚠️ `leave_rules` - Optional (from coco_schema_extensions.sql)
- ⚠️ `agent_tasks` - Optional (from coco_schema_extensions.sql)

---

## 🚨 Troubleshooting

### Error: "schema hrb_emp_lms does not exist"
- **Solution**: The schema is created by `database-setup.sql`. Make sure you ran it.

### Error: "relation does not exist"
- **Solution**: Check that you ran all the required SQL files in the correct order.

### Error: "permission denied"
- **Solution**: Make sure you're using the `postgres` user or a user with CREATE privileges.

### Error: "database hr_chatbot does not exist"
- **Solution**: Create the database first:
  ```sql
  CREATE DATABASE hr_chatbot;
  ```

---

## 📝 Next Steps

1. Run the SQL scripts using the commands above (adjust psql path as needed)
2. Verify using the verification script
3. Test endpoints using the Python test script (after starting the API server)
4. Review `README_DATABASE_SETUP.md` for detailed documentation

---

**Status**: ✅ All scripts prepared and ready for execution  
**Action Required**: Run the SQL scripts manually using psql or pgAdmin






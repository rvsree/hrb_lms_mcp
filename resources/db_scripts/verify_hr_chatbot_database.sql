-- ============================================================================
-- HR_CHATBOT DATABASE - VERIFICATION SCRIPT
-- Database: hr_chatbot (PostgreSQL)
-- ============================================================================
-- This script verifies that all required tables exist and have sample data
-- ============================================================================
-- Usage: psql -d hr_chatbot -f verify_hr_chatbot_database.sql
-- ============================================================================

\echo '============================================================================'
\echo 'HR_CHATBOT DATABASE - VERIFICATION'
\echo '============================================================================'
\echo ''

-- ============================================================================
-- PART 1: VERIFY HRB_EMP_LMS SCHEMA
-- ============================================================================

\echo 'PART 1: Verifying hrb_emp_lms schema...'
\echo ''

-- Check schema exists
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'hrb_emp_lms')
        THEN '✅ Schema hrb_emp_lms exists'
        ELSE '❌ Schema hrb_emp_lms NOT FOUND'
    END as schema_status;

-- Check tables exist
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'hrb_emp_lms' AND table_name = 'employees')
        THEN '✅ Table hrb_emp_lms.employees exists'
        ELSE '❌ Table hrb_emp_lms.employees NOT FOUND'
    END as table_status
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'hrb_emp_lms' AND table_name = 'leave_types')
        THEN '✅ Table hrb_emp_lms.leave_types exists'
        ELSE '❌ Table hrb_emp_lms.leave_types NOT FOUND'
    END
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'hrb_emp_lms' AND table_name = 'leave_balances')
        THEN '✅ Table hrb_emp_lms.leave_balances exists'
        ELSE '❌ Table hrb_emp_lms.leave_balances NOT FOUND'
    END
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'hrb_emp_lms' AND table_name = 'leave_requests')
        THEN '✅ Table hrb_emp_lms.leave_requests exists'
        ELSE '❌ Table hrb_emp_lms.leave_requests NOT FOUND'
    END
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'hrb_emp_lms' AND table_name = 'hitl_requests')
        THEN '✅ Table hrb_emp_lms.hitl_requests exists'
        ELSE '❌ Table hrb_emp_lms.hitl_requests NOT FOUND'
    END
ORDER BY table_status;

-- Count rows in each table
\echo ''
\echo 'Row counts in hrb_emp_lms schema:'
SELECT 
    'employees' as table_name,
    COUNT(*) as row_count
FROM hrb_emp_lms.employees
UNION ALL
SELECT 
    'leave_types',
    COUNT(*)
FROM hrb_emp_lms.leave_types
UNION ALL
SELECT 
    'leave_balances',
    COUNT(*)
FROM hrb_emp_lms.leave_balances
UNION ALL
SELECT 
    'leave_requests',
    COUNT(*)
FROM hrb_emp_lms.leave_requests
UNION ALL
SELECT 
    'hitl_requests',
    COUNT(*)
FROM hrb_emp_lms.hitl_requests
ORDER BY table_name;

-- Verify test employees exist
\echo ''
\echo 'Test employees verification:'
SELECT 
    CASE 
        WHEN COUNT(*) = 3 THEN '✅ All 3 test employees found (emp_12345, emp_67890, emp_11111)'
        ELSE '❌ Missing test employees. Found: ' || COUNT(*) || ', Expected: 3'
    END as test_employees_status
FROM hrb_emp_lms.employees
WHERE employee_id IN ('emp_12345', 'emp_67890', 'emp_11111');

SELECT 
    employee_id,
    name,
    email,
    hire_date,
    department
FROM hrb_emp_lms.employees
WHERE employee_id IN ('emp_12345', 'emp_67890', 'emp_11111')
ORDER BY employee_id;

-- Verify leave balances for test employees
\echo ''
\echo 'Leave balances for test employees:'
SELECT 
    e.employee_id,
    lt.code as leave_type,
    lb.accrued,
    lb.used,
    lb.available,
    lb.year
FROM hrb_emp_lms.employees e
JOIN hrb_emp_lms.leave_balances lb ON lb.employee_id = e.id
JOIN hrb_emp_lms.leave_types lt ON lt.id = lb.leave_type_id
WHERE e.employee_id IN ('emp_12345', 'emp_67890', 'emp_11111')
ORDER BY e.employee_id, lt.code;

-- ============================================================================
-- PART 2: VERIFY HRB_COPILOT TABLES (Public Schema)
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'PART 2: Verifying hrb_copilot tables (public schema)...'
\echo '============================================================================'
\echo ''

-- Check required tables exist
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'chat_sessions')
        THEN '✅ Table chat_sessions exists'
        ELSE '❌ Table chat_sessions NOT FOUND'
    END as table_status
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'chat_history')
        THEN '✅ Table chat_history exists'
        ELSE '❌ Table chat_history NOT FOUND'
    END
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_feedback')
        THEN '✅ Table user_feedback exists'
        ELSE '❌ Table user_feedback NOT FOUND'
    END
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'policy_versions')
        THEN '✅ Table policy_versions exists'
        ELSE '⚠️  Table policy_versions NOT FOUND (optional - from coco_schema_extensions.sql)'
    END
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leave_rules')
        THEN '✅ Table leave_rules exists'
        ELSE '⚠️  Table leave_rules NOT FOUND (optional - from coco_schema_extensions.sql)'
    END
UNION ALL
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'agent_tasks')
        THEN '✅ Table agent_tasks exists'
        ELSE '⚠️  Table agent_tasks NOT FOUND (optional - from coco_schema_extensions.sql)'
    END
ORDER BY table_status;

-- Count rows (only if tables exist)
\echo ''
\echo 'Row counts in public schema (if tables exist):'
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'chat_sessions') THEN
        RAISE NOTICE 'chat_sessions: % rows', (SELECT COUNT(*) FROM chat_sessions);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'chat_history') THEN
        RAISE NOTICE 'chat_history: % rows', (SELECT COUNT(*) FROM chat_history);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_feedback') THEN
        RAISE NOTICE 'user_feedback: % rows', (SELECT COUNT(*) FROM user_feedback);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'policy_versions') THEN
        RAISE NOTICE 'policy_versions: % rows', (SELECT COUNT(*) FROM policy_versions);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'leave_rules') THEN
        RAISE NOTICE 'leave_rules: % rows', (SELECT COUNT(*) FROM leave_rules);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'agent_tasks') THEN
        RAISE NOTICE 'agent_tasks: % rows', (SELECT COUNT(*) FROM agent_tasks);
    END IF;
END $$;

-- ============================================================================
-- SUMMARY
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'VERIFICATION SUMMARY'
\echo '============================================================================'
\echo ''

SELECT 
    'hrb_emp_lms schema tables' as category,
    COUNT(*) as tables_found,
    CASE 
        WHEN COUNT(*) = 5 THEN '✅ All tables found'
        ELSE '❌ Missing tables'
    END as status
FROM information_schema.tables 
WHERE table_schema = 'hrb_emp_lms' 
  AND table_name IN ('employees', 'leave_types', 'leave_balances', 'leave_requests', 'hitl_requests')
UNION ALL
SELECT 
    'Required hrb_copilot tables (chat_sessions, chat_history, user_feedback)',
    COUNT(*),
    CASE 
        WHEN COUNT(*) = 3 THEN '✅ All required tables found'
        ELSE '❌ Missing required tables'
    END
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('chat_sessions', 'chat_history', 'user_feedback')
UNION ALL
SELECT 
    'Optional hrb_copilot tables (policy_versions, leave_rules, agent_tasks)',
    COUNT(*),
    CASE 
        WHEN COUNT(*) = 3 THEN '✅ All optional tables found'
        WHEN COUNT(*) > 0 THEN '⚠️  Some optional tables found'
        ELSE '⚠️  Optional tables not found (run coco_schema_extensions.sql if needed)'
    END
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('policy_versions', 'leave_rules', 'agent_tasks');

\echo ''
\echo '============================================================================'
\echo 'VERIFICATION COMPLETE'
\echo '============================================================================'
\echo ''






-- ============================================================================
-- HR_CHATBOT DATABASE - COMPLETE MASTER SETUP SCRIPT
-- Database: hr_chatbot (PostgreSQL)
-- Schemas: hrb_emp_lms (Leave Management Service), public (hrb_copilot tables)
-- ============================================================================
-- This script sets up the complete hr_chatbot database with:
-- 1. hrb_emp_lms schema (Leave Management Service tables)
-- 2. Public schema tables for hrb_copilot (chat_sessions, chat_history, user_feedback, policy_versions, leave_rules, agent_tasks)
-- ============================================================================
-- IMPORTANT: 
-- - Run this script as a PostgreSQL superuser or user with CREATE SCHEMA privileges
-- - Database 'hr_chatbot' must already exist
-- - Ensure all referenced SQL files are in the same directory or adjust paths
-- ============================================================================
-- Usage: 
--   psql -h localhost -p 5432 -U postgres -d hr_chatbot -f setup_hr_chatbot_master.sql
-- ============================================================================

\echo '============================================================================'
\echo 'HR_CHATBOT DATABASE - COMPLETE SETUP'
\echo 'Database: hr_chatbot'
\echo 'Schemas: hrb_emp_lms, public'
\echo '============================================================================'
\echo ''

-- Set client encoding
SET client_encoding = 'UTF8';

-- ============================================================================
-- PART 1: SETUP HRB_EMP_LMS SCHEMA (Leave Management Service)
-- ============================================================================

\echo 'PART 1: Setting up hrb_emp_lms schema...'
\echo '  - Creating schema: hrb_emp_lms'
\echo '  - Creating tables: employees, leave_types, leave_balances, leave_requests, hitl_requests'
\echo '  - Inserting sample data including test employees (emp_12345, emp_67890, emp_11111)'
\echo ''

-- Source the hrb_emp_lms database setup script
-- Note: This assumes database-setup.sql is in the same directory
\i database-setup.sql

\echo ''
\echo 'PART 1 COMPLETE: hrb_emp_lms schema setup finished'
\echo ''

-- ============================================================================
-- PART 2: SETUP HRB_COPILOT TABLES (Public Schema)
-- ============================================================================

\echo '============================================================================'
\echo 'PART 2: Setting up hrb_copilot tables in public schema...'
\echo '  - Tables: chat_sessions, chat_history, user_feedback'
\echo '  - Tables: policy_versions, leave_rules, agent_tasks (from coco schema extensions)'
\echo ''
\echo 'NOTE: The following SQL files need to be copied to this directory or paths adjusted:'
\echo '  - hr_chatbot_schema.sql (from hrb_copilot project)'
\echo '  - hr_chatbot_schema_dml.sql (from hrb_copilot project)'
\echo '  - coco_schema_extensions.sql (from hrb_copilot project)'
\echo '  - coco_schema_dml.sql (from hrb_copilot project)'
\echo ''
\echo 'OR run them separately after this script:'
\echo '  psql -d hr_chatbot -f <path_to_hrb_copilot>/hr_chatbot_schema.sql'
\echo '  psql -d hr_chatbot -f <path_to_hrb_copilot>/hr_chatbot_schema_dml.sql'
\echo '  psql -d hr_chatbot -f <path_to_hrb_copilot>/coco_schema_extensions.sql'
\echo '  psql -d hr_chatbot -f <path_to_hrb_copilot>/coco_schema_dml.sql'
\echo ''

-- Check if files exist before sourcing (optional - uncomment if files are in same directory)
-- \if :{?hr_chatbot_schema_exists}
--     \echo '  Running hr_chatbot_schema.sql...'
--     \i hr_chatbot_schema.sql
-- \else
--     \echo '  WARNING: hr_chatbot_schema.sql not found - skipping'
-- \endif

\echo ''
\echo 'PART 2: hrb_copilot tables should be set up separately (see instructions above)'
\echo ''

-- ============================================================================
-- PART 3: VERIFICATION
-- ============================================================================

\echo '============================================================================'
\echo 'PART 3: Verification'
\echo '============================================================================'
\echo ''

-- Verify hrb_emp_lms schema tables
\echo 'Verifying hrb_emp_lms schema tables...'
SELECT 
    'hrb_emp_lms.employees' as table_name,
    COUNT(*) as row_count
FROM hrb_emp_lms.employees
UNION ALL
SELECT 
    'hrb_emp_lms.leave_types',
    COUNT(*)
FROM hrb_emp_lms.leave_types
UNION ALL
SELECT 
    'hrb_emp_lms.leave_balances',
    COUNT(*)
FROM hrb_emp_lms.leave_balances
UNION ALL
SELECT 
    'hrb_emp_lms.leave_requests',
    COUNT(*)
FROM hrb_emp_lms.leave_requests
UNION ALL
SELECT 
    'hrb_emp_lms.hitl_requests',
    COUNT(*)
FROM hrb_emp_lms.hitl_requests
ORDER BY table_name;

\echo ''
\echo 'Verifying test employees exist...'
SELECT 
    employee_id,
    name,
    email,
    hire_date
FROM hrb_emp_lms.employees
WHERE employee_id IN ('emp_12345', 'emp_67890', 'emp_11111')
ORDER BY employee_id;

\echo ''
\echo '============================================================================'
\echo 'SETUP COMPLETE!'
\echo '============================================================================'
\echo ''
\echo 'Next steps:'
\echo '  1. Run hrb_copilot schema files separately (see PART 2 instructions above)'
\echo '  2. Run verification script: verify_hr_chatbot_database.sql'
\echo '  3. Test endpoints using: test_hr_chatbot_endpoints.py'
\echo ''






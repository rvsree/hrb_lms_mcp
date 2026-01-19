-- ============================================================================
-- HR_CHATBOT DATABASE - COMPLETE SETUP SCRIPT
-- Database: hr_chatbot (PostgreSQL)
-- Schemas: hrb_emp_lms, public (for hrb_copilot tables)
-- ============================================================================
-- This script sets up the complete hr_chatbot database with:
-- 1. hrb_emp_lms schema (Leave Management Service tables)
-- 2. Public schema tables for hrb_copilot (chat_sessions, chat_history, user_feedback, etc.)
-- ============================================================================
-- IMPORTANT: Run this script as a PostgreSQL superuser or user with CREATE SCHEMA privileges
-- Usage: psql -d hr_chatbot -f setup_hr_chatbot_database.sql
-- ============================================================================

\echo 'Starting hr_chatbot database setup...'

-- ============================================================================
-- PART 1: SETUP HRB_EMP_LMS SCHEMA
-- ============================================================================

\echo 'Setting up hrb_emp_lms schema...'
\i database-setup.sql

-- ============================================================================
-- PART 2: SETUP HRB_COPILOT TABLES (Public Schema)
-- ============================================================================
-- Note: hrb_copilot tables are created in public schema
-- These files should be in: c:\workspace\poc\chatbot\agentic_ai\src\app\common\db_scripts\postgres\

\echo 'Setting up hrb_copilot tables in public schema...'

-- Note: You need to manually copy or reference the hrb_copilot schema files here
-- Or run them separately:
-- psql -d hr_chatbot -f <path_to_hrb_copilot>/hr_chatbot_schema.sql
-- psql -d hr_chatbot -f <path_to_hrb_copilot>/hr_chatbot_schema_dml.sql
-- psql -d hr_chatbot -f <path_to_hrb_copilot>/coco_schema_extensions.sql
-- psql -d hr_chatbot -f <path_to_hrb_copilot>/coco_schema_dml.sql

\echo 'hr_chatbot database setup complete!'






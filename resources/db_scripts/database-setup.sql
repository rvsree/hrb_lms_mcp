-- ============================================================================
-- LEAVE MANAGEMENT SERVICE - DATABASE SETUP
-- Complete database schema and sample data
-- Database: hr_chatbot (PostgreSQL)
-- Schema: hrb_emp_lms
-- ============================================================================

-- ============================================================================
-- PART 0: CREATE SCHEMA
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS hrb_emp_lms;
SET search_path TO hrb_emp_lms, public;

-- ============================================================================
-- PART 1: CREATE TABLES
-- ============================================================================

-- Employees Table
CREATE TABLE IF NOT EXISTS hrb_emp_lms.employees (
    id BIGSERIAL PRIMARY KEY,
    employee_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    department VARCHAR(100),
    manager_id BIGINT REFERENCES hrb_emp_lms.employees(id),
    hire_date DATE,
    employment_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Leave Types Table
CREATE TABLE IF NOT EXISTS hrb_emp_lms.leave_types (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    accrual_rate DECIMAL(5,2),
    max_carryover INTEGER,
    requires_approval BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Leave Balances Table
CREATE TABLE IF NOT EXISTS hrb_emp_lms.leave_balances (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT REFERENCES hrb_emp_lms.employees(id) NOT NULL,
    leave_type_id BIGINT REFERENCES hrb_emp_lms.leave_types(id) NOT NULL,
    accrued DECIMAL(5,2) DEFAULT 0,
    used DECIMAL(5,2) DEFAULT 0,
    available DECIMAL(5,2) GENERATED ALWAYS AS (accrued - used) STORED,
    year INTEGER NOT NULL,
    UNIQUE(employee_id, leave_type_id, year),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Leave Requests Table
CREATE TABLE IF NOT EXISTS hrb_emp_lms.leave_requests (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT REFERENCES hrb_emp_lms.employees(id) NOT NULL,
    leave_type_id BIGINT REFERENCES hrb_emp_lms.leave_types(id) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days DECIMAL(5,2) NOT NULL,
    reason TEXT,
    status VARCHAR(50) DEFAULT 'PENDING',
    approver_id BIGINT REFERENCES hrb_emp_lms.employees(id),
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_date >= start_date)
);

-- HITL Requests Table
CREATE TABLE IF NOT EXISTS hrb_emp_lms.hitl_requests (
    id BIGSERIAL PRIMARY KEY,
    request_type VARCHAR(50) NOT NULL,
    related_entity_type VARCHAR(50),
    related_entity_id BIGINT,
    employee_id BIGINT REFERENCES hrb_emp_lms.employees(id),
    query TEXT NOT NULL,
    context JSONB,
    status VARCHAR(50) DEFAULT 'PENDING',
    assigned_to VARCHAR(255),
    response TEXT,
    responded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_leave_balances_employee ON hrb_emp_lms.leave_balances(employee_id, year);
CREATE INDEX IF NOT EXISTS idx_leave_requests_employee ON hrb_emp_lms.leave_requests(employee_id, status);
CREATE INDEX IF NOT EXISTS idx_leave_requests_approver ON hrb_emp_lms.leave_requests(approver_id, status);
CREATE INDEX IF NOT EXISTS idx_hitl_requests_status ON hrb_emp_lms.hitl_requests(status, assigned_to);
CREATE INDEX IF NOT EXISTS idx_employees_manager ON hrb_emp_lms.employees(manager_id);
CREATE INDEX IF NOT EXISTS idx_employees_employee_id ON hrb_emp_lms.employees(employee_id);

-- ============================================================================
-- PART 2: INSERT SAMPLE DATA
-- ============================================================================

-- Insert Leave Types
INSERT INTO hrb_emp_lms.leave_types (code, name, accrual_rate, max_carryover, requires_approval) VALUES
('PTO', 'Paid Time Off', 1.25, 5, true),
('SICK', 'Sick Leave', 0.83, 0, false),
('UNPAID', 'Unpaid Leave', 0, 0, true),
('SABBATICAL', 'Sabbatical Leave', 0, 0, true),
('MATERNITY', 'Maternity Leave', 0, 0, true),
('PATERNITY', 'Paternity Leave', 0, 0, true)
ON CONFLICT (code) DO NOTHING;

-- Insert Managers (must be inserted first)
INSERT INTO hrb_emp_lms.employees (employee_id, name, email, department, manager_id, hire_date, employment_type) VALUES
('MGR001', 'Alice Johnson', 'alice.johnson@company.com', 'Engineering', NULL, '2020-01-15', 'FULL_TIME'),
('MGR002', 'Bob Smith', 'bob.smith@company.com', 'Sales', NULL, '2019-03-20', 'FULL_TIME'),
('MGR003', 'Carol Williams', 'carol.williams@company.com', 'HR', NULL, '2018-06-10', 'FULL_TIME'),
('MGR004', 'David Brown', 'david.brown@company.com', 'Marketing', NULL, '2021-02-01', 'FULL_TIME'),
('MGR005', 'Emma Davis', 'emma.davis@company.com', 'Finance', NULL, '2019-11-05', 'FULL_TIME')
ON CONFLICT (employee_id) DO NOTHING;

-- Insert Test Employees for hrb_copilot (emp_12345, emp_67890, emp_11111)
INSERT INTO hrb_emp_lms.employees (employee_id, name, email, department, manager_id, hire_date, employment_type) VALUES
-- Test employees used by hrb_copilot
('emp_12345', 'Test Employee 12345', 'emp_12345@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2022-08-15', 'FULL_TIME'),
('emp_67890', 'Test Employee 67890', 'emp_67890@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2020-03-15', 'FULL_TIME'),
('emp_11111', 'Test Employee 11111', 'emp_11111@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2024-11-01', 'FULL_TIME')
ON CONFLICT (employee_id) DO NOTHING;

-- Insert Employees (50 employees)
INSERT INTO hrb_emp_lms.employees (employee_id, name, email, department, manager_id, hire_date, employment_type) VALUES
-- Engineering Department (MGR001)
('EMP001', 'John Doe', 'john.doe@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2021-05-10', 'FULL_TIME'),
('EMP002', 'Jane Smith', 'jane.smith@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2021-08-15', 'FULL_TIME'),
('EMP003', 'Michael Johnson', 'michael.johnson@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2022-01-20', 'FULL_TIME'),
('EMP004', 'Sarah Williams', 'sarah.williams@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2022-03-12', 'FULL_TIME'),
('EMP005', 'Robert Brown', 'robert.brown@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2022-06-01', 'FULL_TIME'),
('EMP006', 'Lisa Davis', 'lisa.davis@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2022-09-15', 'FULL_TIME'),
('EMP007', 'James Wilson', 'james.wilson@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2023-01-10', 'FULL_TIME'),
('EMP008', 'Mary Moore', 'mary.moore@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2023-04-20', 'FULL_TIME'),
('EMP009', 'William Taylor', 'william.taylor@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2023-07-05', 'FULL_TIME'),
('EMP010', 'Patricia Anderson', 'patricia.anderson@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2023-10-12', 'FULL_TIME'),
-- Sales Department (MGR002)
('EMP011', 'Richard Thomas', 'richard.thomas@company.com', 'Sales', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1), '2021-02-14', 'FULL_TIME'),
('EMP012', 'Jennifer Jackson', 'jennifer.jackson@company.com', 'Sales', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1), '2021-05-20', 'FULL_TIME'),
('EMP013', 'Joseph White', 'joseph.white@company.com', 'Sales', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1), '2021-09-01', 'FULL_TIME'),
('EMP014', 'Linda Harris', 'linda.harris@company.com', 'Sales', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1), '2022-01-15', 'FULL_TIME'),
('EMP015', 'Thomas Martin', 'thomas.martin@company.com', 'Sales', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1), '2022-04-10', 'FULL_TIME'),
('EMP016', 'Barbara Thompson', 'barbara.thompson@company.com', 'Sales', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1), '2022-07-22', 'FULL_TIME'),
('EMP017', 'Charles Garcia', 'charles.garcia@company.com', 'Sales', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1), '2022-11-05', 'FULL_TIME'),
('EMP018', 'Elizabeth Martinez', 'elizabeth.martinez@company.com', 'Sales', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1), '2023-02-18', 'FULL_TIME'),
('EMP019', 'Christopher Robinson', 'christopher.robinson@company.com', 'Sales', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1), '2023-05-30', 'FULL_TIME'),
('EMP020', 'Susan Clark', 'susan.clark@company.com', 'Sales', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1), '2023-09-12', 'FULL_TIME'),
-- HR Department (MGR003)
('EMP021', 'Daniel Rodriguez', 'daniel.rodriguez@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2021-03-10', 'FULL_TIME'),
('EMP022', 'Jessica Lewis', 'jessica.lewis@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2021-06-15', 'FULL_TIME'),
('EMP023', 'Matthew Walker', 'matthew.walker@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2021-10-20', 'FULL_TIME'),
('EMP024', 'Sarah Hall', 'sarah.hall@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2022-02-01', 'FULL_TIME'),
('EMP025', 'Anthony Allen', 'anthony.allen@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2022-05-12', 'FULL_TIME'),
('EMP026', 'Karen Young', 'karen.young@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2022-08-25', 'FULL_TIME'),
('EMP027', 'Mark King', 'mark.king@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2023-01-08', 'FULL_TIME'),
('EMP028', 'Nancy Wright', 'nancy.wright@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2023-04-20', 'FULL_TIME'),
-- Marketing Department (MGR004)
('EMP029', 'Donald Lopez', 'donald.lopez@company.com', 'Marketing', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR004' LIMIT 1), '2021-04-05', 'FULL_TIME'),
('EMP030', 'Betty Hill', 'betty.hill@company.com', 'Marketing', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR004' LIMIT 1), '2021-07-18', 'FULL_TIME'),
('EMP031', 'Steven Scott', 'steven.scott@company.com', 'Marketing', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR004' LIMIT 1), '2021-11-02', 'FULL_TIME'),
('EMP032', 'Helen Green', 'helen.green@company.com', 'Marketing', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR004' LIMIT 1), '2022-03-15', 'FULL_TIME'),
('EMP033', 'Paul Adams', 'paul.adams@company.com', 'Marketing', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR004' LIMIT 1), '2022-06-28', 'FULL_TIME'),
('EMP034', 'Sandra Baker', 'sandra.baker@company.com', 'Marketing', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR004' LIMIT 1), '2022-10-10', 'FULL_TIME'),
('EMP035', 'Andrew Nelson', 'andrew.nelson@company.com', 'Marketing', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR004' LIMIT 1), '2023-01-22', 'FULL_TIME'),
('EMP036', 'Donna Carter', 'donna.carter@company.com', 'Marketing', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR004' LIMIT 1), '2023-05-05', 'FULL_TIME'),
-- Finance Department (MGR005)
('EMP037', 'Joshua Mitchell', 'joshua.mitchell@company.com', 'Finance', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR005' LIMIT 1), '2021-01-20', 'FULL_TIME'),
('EMP038', 'Carol Perez', 'carol.perez@company.com', 'Finance', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR005' LIMIT 1), '2021-05-03', 'FULL_TIME'),
('EMP039', 'Kenneth Roberts', 'kenneth.roberts@company.com', 'Finance', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR005' LIMIT 1), '2021-08-16', 'FULL_TIME'),
('EMP040', 'Ruth Turner', 'ruth.turner@company.com', 'Finance', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR005' LIMIT 1), '2022-01-28', 'FULL_TIME'),
('EMP041', 'Kevin Phillips', 'kevin.phillips@company.com', 'Finance', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR005' LIMIT 1), '2022-05-11', 'FULL_TIME'),
('EMP042', 'Sharon Campbell', 'sharon.campbell@company.com', 'Finance', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR005' LIMIT 1), '2022-09-23', 'FULL_TIME'),
('EMP043', 'Brian Parker', 'brian.parker@company.com', 'Finance', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR005' LIMIT 1), '2023-02-05', 'FULL_TIME'),
('EMP044', 'Michelle Evans', 'michelle.evans@company.com', 'Finance', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR005' LIMIT 1), '2023-06-18', 'FULL_TIME'),
-- Part-time and Contractors
('EMP045', 'Edward Edwards', 'edward.edwards@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2023-03-01', 'PART_TIME'),
('EMP046', 'Kimberly Collins', 'kimberly.collins@company.com', 'Sales', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1), '2023-06-15', 'PART_TIME'),
('EMP047', 'Ronald Stewart', 'ronald.stewart@company.com', 'Marketing', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR004' LIMIT 1), '2023-01-10', 'CONTRACTOR'),
('EMP048', 'Deborah Sanchez', 'deborah.sanchez@company.com', 'HR', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1), '2023-04-20', 'PART_TIME'),
('EMP049', 'Timothy Morris', 'timothy.morris@company.com', 'Finance', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR005' LIMIT 1), '2023-08-01', 'CONTRACTOR'),
('EMP050', 'Rachel Rogers', 'rachel.rogers@company.com', 'Engineering', (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1), '2023-11-15', 'PART_TIME')
ON CONFLICT (employee_id) DO NOTHING;

-- Insert Leave Balances for 2025 (including test employees)
INSERT INTO hrb_emp_lms.leave_balances (employee_id, leave_type_id, accrued, used, year) 
SELECT 
    e.id,
    lt.id,
    CASE 
        WHEN lt.code = 'PTO' THEN 
            CASE 
                WHEN e.hire_date < '2024-01-01' THEN 20.0
                WHEN e.hire_date < '2024-07-01' THEN 15.0
                WHEN e.hire_date < '2025-01-01' THEN 10.0
                ELSE 5.0
            END
        WHEN lt.code = 'SICK' THEN 
            CASE 
                WHEN e.hire_date < '2024-01-01' THEN 10.0
                WHEN e.hire_date < '2024-07-01' THEN 7.5
                WHEN e.hire_date < '2025-01-01' THEN 5.0
                ELSE 2.5
            END
        ELSE 0
    END as accrued,
    CASE 
        WHEN lt.code = 'PTO' THEN 
            CASE 
                WHEN e.id % 10 = 0 THEN 8.0
                WHEN e.id % 10 < 3 THEN 5.0
                WHEN e.id % 10 < 6 THEN 3.0
                ELSE 1.5
            END
        WHEN lt.code = 'SICK' THEN 
            CASE 
                WHEN e.id % 10 = 0 THEN 4.0
                WHEN e.id % 10 < 3 THEN 2.5
                WHEN e.id % 10 < 6 THEN 1.5
                ELSE 0.5
            END
        ELSE 0
    END as used,
    2025
FROM hrb_emp_lms.employees e
CROSS JOIN hrb_emp_lms.leave_types lt
WHERE lt.code IN ('PTO', 'SICK')
ON CONFLICT (employee_id, leave_type_id, year) DO NOTHING;

-- Insert Leave Requests (using subqueries for reliability)
INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id, approved_at) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP006' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-01-15'::DATE, '2025-01-17'::DATE, 3.0, 'Family vacation', 'APPROVED',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1),
    '2025-01-10 10:00:00'::TIMESTAMP
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP006')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001')
ON CONFLICT DO NOTHING;

INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id, approved_at) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP007' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-02-10'::DATE, '2025-02-12'::DATE, 3.0, 'Personal time', 'APPROVED',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1),
    '2025-02-05 14:30:00'::TIMESTAMP
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP007')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001')
ON CONFLICT DO NOTHING;

INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id, approved_at) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP011' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-03-20'::DATE, '2025-03-22'::DATE, 3.0, 'Holiday', 'APPROVED',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1),
    '2025-03-15 09:00:00'::TIMESTAMP
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP011')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002')
ON CONFLICT DO NOTHING;

INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id, approved_at) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP012' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'SICK' LIMIT 1),
    '2025-04-05'::DATE, '2025-04-05'::DATE, 1.0, 'Sick day', 'APPROVED',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1),
    '2025-04-05 08:00:00'::TIMESTAMP
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP012')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'SICK')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002')
ON CONFLICT DO NOTHING;

INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id, approved_at) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP021' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-05-10'::DATE, '2025-05-14'::DATE, 5.0, 'Vacation', 'APPROVED',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1),
    '2025-05-01 11:00:00'::TIMESTAMP
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP021')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003')
ON CONFLICT DO NOTHING;

-- Pending requests
INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP008' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-12-20'::DATE, '2025-12-24'::DATE, 5.0, 'Christmas vacation', 'PENDING',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1)
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP008')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001')
ON CONFLICT DO NOTHING;

INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP013' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-12-18'::DATE, '2025-12-20'::DATE, 3.0, 'Year end break', 'PENDING',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1)
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP013')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002')
ON CONFLICT DO NOTHING;

INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP022' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-12-15'::DATE, '2025-12-17'::DATE, 3.0, 'Personal time', 'PENDING',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003' LIMIT 1)
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP022')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR003')
ON CONFLICT DO NOTHING;

INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP029' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-12-22'::DATE, '2025-12-27'::DATE, 6.0, 'Holiday season', 'PENDING',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR004' LIMIT 1)
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP029')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR004')
ON CONFLICT DO NOTHING;

INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP037' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-12-19'::DATE, '2025-12-23'::DATE, 5.0, 'Family time', 'PENDING',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR005' LIMIT 1)
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP037')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR005')
ON CONFLICT DO NOTHING;

-- Rejected requests
INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP009' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-06-01'::DATE, '2025-06-10'::DATE, 10.0, 'Long vacation', 'REJECTED',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1)
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP009')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001')
ON CONFLICT DO NOTHING;

INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP014' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-07-15'::DATE, '2025-07-20'::DATE, 6.0, 'Personal', 'REJECTED',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002' LIMIT 1)
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP014')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR002')
ON CONFLICT DO NOTHING;

-- PENDING_HITL request
INSERT INTO hrb_emp_lms.leave_requests (employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id) 
SELECT 
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'EMP010' LIMIT 1),
    (SELECT id FROM hrb_emp_lms.leave_types WHERE code = 'PTO' LIMIT 1),
    '2025-12-20'::DATE, '2025-12-30'::DATE, 11.0, 'Extended vacation', 'PENDING_HITL',
    (SELECT id FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001' LIMIT 1)
WHERE EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'EMP010')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.leave_types WHERE code = 'PTO')
  AND EXISTS (SELECT 1 FROM hrb_emp_lms.employees WHERE employee_id = 'MGR001')
ON CONFLICT DO NOTHING;

-- Insert HITL Request
INSERT INTO hrb_emp_lms.hitl_requests (request_type, related_entity_type, related_entity_id, employee_id, query, context, status, assigned_to) 
SELECT 
    'LEAVE_EXCEPTION',
    'leave_request',
    lr.id,
    lr.employee_id,
    'Employee requests 11 days PTO but only has limited balance available. Requires exception approval.',
    jsonb_build_object(
        'leave_request_id', lr.id,
        'requested_days', 11.0,
        'available_balance', 3.5,
        'shortfall', 7.5
    ),
    'PENDING',
    'hr-team@company.com'
FROM hrb_emp_lms.leave_requests lr
WHERE lr.status = 'PENDING_HITL'
LIMIT 1
ON CONFLICT DO NOTHING;

-- Reset search_path
RESET search_path;

-- ============================================================================
-- PART 3: VERIFICATION
-- ============================================================================

-- Verify tables
SELECT 'Tables in hrb_emp_lms schema: ' || COUNT(*) as verification 
FROM information_schema.tables 
WHERE table_schema = 'hrb_emp_lms' 
  AND table_name IN ('employees', 'leave_types', 'leave_balances', 'leave_requests', 'hitl_requests');

-- Verify data
SELECT 'Employees in hrb_emp_lms: ' || COUNT(*) as count FROM hrb_emp_lms.employees;
SELECT 'Leave Types in hrb_emp_lms: ' || COUNT(*) as count FROM hrb_emp_lms.leave_types;
SELECT 'Leave Balances in hrb_emp_lms: ' || COUNT(*) as count FROM hrb_emp_lms.leave_balances;
SELECT 'Leave Requests in hrb_emp_lms: ' || COUNT(*) as count FROM hrb_emp_lms.leave_requests;
SELECT 'HITL Requests in hrb_emp_lms: ' || COUNT(*) as count FROM hrb_emp_lms.hitl_requests;

-- Verify test employees exist
SELECT 'Test Employees (emp_12345, emp_67890, emp_11111): ' || COUNT(*) as count 
FROM hrb_emp_lms.employees 
WHERE employee_id IN ('emp_12345', 'emp_67890', 'emp_11111');

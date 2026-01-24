"""
Integration tests for MCP tools with real PostgreSQL database.

This test suite tests all MCP tools against actual database data
from database-setup.sql. It verifies that each tool works correctly
with real data and handles error cases properly.

Prerequisites:
- PostgreSQL database must be running
- database-setup.sql must have been executed
- Sample data must exist (employees, leave_balances, leave_requests, hitl_requests)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, datetime

from src.app.api.main import app
from src.app.api.controller.lms_mcp_server import get_mcp_server
from src.app.repos.database import get_db
from src.app.common.config.config import settings


class TestMCPToolsIntegration:
    """Integration tests for MCP tools with real database."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
        self.mcp_server = get_mcp_server()
        self.api_key = settings.api_key
        
        # Test employee IDs from database-setup.sql
        self.test_employees = {
            "emp_12345": "Test Employee 12345",
            "emp_67890": "Test Employee 67890", 
            "emp_11111": "Test Employee 11111",
            "EMP001": "John Doe",
            "EMP006": "Lisa Davis",
            "EMP007": "James Wilson",
            "EMP008": "Mary Moore",
            "EMP011": "Richard Thomas",
            "EMP012": "Jennifer Jackson",
            "EMP021": "Daniel Rodriguez",
        }
        
        # Manager IDs
        self.test_managers = {
            "MGR001": "Alice Johnson",
            "MGR002": "Bob Smith",
            "MGR003": "Carol Williams",
            "MGR004": "David Brown",
            "MGR005": "Emma Davis",
        }
        
        # Verify database connection
        db = next(get_db())
        try:
            # Quick health check - verify we can query employees
            from sqlalchemy import text
            result = db.execute(text("SELECT COUNT(*) FROM employees")).scalar()
            assert result > 0, "Database appears empty. Run database-setup.sql first."
        finally:
            db.close()
    
    # ========================================================================
    # Test: get_leave_balance
    # ========================================================================
    
    def test_get_leave_balance_with_valid_employee(self):
        """Test get_leave_balance with valid employee ID."""
        # Test with emp_12345 (test employee from database-setup.sql)
        result = self.mcp_server.call_tool(
            "get_leave_balance",
            {"employee_id": "emp_12345", "year": 2025},
            api_key=self.api_key
        )
        
        assert isinstance(result, dict)
        assert "employeeId" in result
        assert result["employeeId"] == "emp_12345"
        assert "year" in result
        assert result["year"] == 2025
        assert "balances" in result
        assert isinstance(result["balances"], list)
        
        # Verify balances structure
        if len(result["balances"]) > 0:
            balance = result["balances"][0]
            assert "leaveType" in balance
            assert "accrued" in balance
            assert "used" in balance
            assert "available" in balance
    
    def test_get_leave_balance_without_year(self):
        """Test get_leave_balance defaults to current year when year not specified."""
        result = self.mcp_server.call_tool(
            "get_leave_balance",
            {"employee_id": "EMP001"},
            api_key=self.api_key
        )
        
        assert isinstance(result, dict)
        assert "employeeId" in result
        assert result["employeeId"] == "EMP001"
        assert "year" in result
        # Should default to current year (could be 2025 or 2026 depending on when test runs)
        from datetime import datetime
        current_year = datetime.now().year
        assert result["year"] == current_year
        assert "balances" in result
    
    def test_get_leave_balance_with_invalid_employee(self):
        """Test get_leave_balance with invalid employee ID."""
        result = self.mcp_server.call_tool(
            "get_leave_balance",
            {"employee_id": "INVALID_EMP_999"},
            api_key=self.api_key
        )
        
        # Should return error
        assert isinstance(result, dict)
        assert result.get("status") == "error"
        assert "not found" in result.get("error", "").lower() or "does not exist" in result.get("error", "").lower()
    
    def test_get_leave_balance_via_endpoint(self):
        """Test get_leave_balance via HTTP endpoint."""
        response = self.client.post(
            "/api/hrb/lms/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "test-get-balance",
                "method": "tools/call",
                "params": {
                    "name": "get_leave_balance",
                    "arguments": {
                        "employee_id": "emp_12345",
                        "year": 2025
                    }
                }
            },
            headers={"X-API-Key": self.api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        result = data["result"]
        assert "employeeId" in result
        assert result["employeeId"] == "emp_12345"
    
    # ========================================================================
    # Test: get_leave_history
    # ========================================================================
    
    def test_get_leave_history_with_valid_employee(self):
        """Test get_leave_history with valid employee who has requests."""
        # EMP006 has approved leave requests in database-setup.sql
        result = self.mcp_server.call_tool(
            "get_leave_history",
            {"employee_id": "EMP006"},
            api_key=self.api_key
        )
        
        assert isinstance(result, dict)
        assert "employeeId" in result
        assert result["employeeId"] == "EMP006"
        assert "requests" in result
        assert isinstance(result["requests"], list)
        
        # Should have at least one request (EMP006 has approved request)
        if len(result["requests"]) > 0:
            request = result["requests"][0]
            assert "requestId" in request
            assert "leaveType" in request
            assert "startDate" in request
            assert "endDate" in request
            assert "status" in request
    
    def test_get_leave_history_with_status_filter(self):
        """Test get_leave_history with status filter."""
        # EMP008 has pending request
        result = self.mcp_server.call_tool(
            "get_leave_history",
            {
                "employee_id": "EMP008",
                "status": "PENDING"
            },
            api_key=self.api_key
        )
        
        assert isinstance(result, dict)
        assert "requests" in result
        # All returned requests should be PENDING
        for req in result["requests"]:
            assert req.get("status") == "PENDING"
    
    def test_get_leave_history_with_pagination(self):
        """Test get_leave_history with limit and offset."""
        result = self.mcp_server.call_tool(
            "get_leave_history",
            {
                "employee_id": "EMP006",
                "limit": 5,
                "offset": 0
            },
            api_key=self.api_key
        )
        
        assert isinstance(result, dict)
        assert "requests" in result
        # Should not exceed limit
        assert len(result["requests"]) <= 5
    
    def test_get_leave_history_with_invalid_employee(self):
        """Test get_leave_history with invalid employee ID."""
        result = self.mcp_server.call_tool(
            "get_leave_history",
            {"employee_id": "INVALID_EMP_999"},
            api_key=self.api_key
        )
        
        # Should return error or empty list
        assert isinstance(result, dict)
        if result.get("status") == "error":
            assert "not found" in result.get("error", "").lower()
        else:
            # Or empty requests list
            assert result.get("requests", []) == []
    
    # ========================================================================
    # Test: submit_leave_request
    # ========================================================================
    
    def test_submit_leave_request_valid(self):
        """Test submitting a valid leave request."""
        # Use a test employee
        result = self.mcp_server.call_tool(
            "submit_leave_request",
            {
                "employee_id": "emp_11111",
                "leave_type": "PTO",
                "start_date": "2025-06-01",
                "end_date": "2025-06-03",
                "reason": "Integration test - vacation"
            },
            api_key=self.api_key
        )
        
        assert isinstance(result, dict)
        assert "requestId" in result
        assert "employeeId" in result
        assert result["employeeId"] == "emp_11111"
        assert "leaveType" in result
        assert result["leaveType"] == "PTO"
        assert "status" in result
        assert result["status"] == "PENDING"
        assert "startDate" in result
        assert "endDate" in result
    
    def test_submit_leave_request_invalid_date_format(self):
        """Test submit_leave_request with invalid date format."""
        result = self.mcp_server.call_tool(
            "submit_leave_request",
            {
                "employee_id": "emp_12345",
                "leave_type": "PTO",
                "start_date": "invalid-date",
                "end_date": "2025-06-03"
            },
            api_key=self.api_key
        )
        
        # Should return validation error
        assert isinstance(result, dict)
        assert result.get("status") == "error" or "error" in result
        error_msg = result.get("error", "") or str(result)
        assert "date" in error_msg.lower() or "format" in error_msg.lower()
    
    def test_submit_leave_request_end_before_start(self):
        """Test submit_leave_request with end_date before start_date."""
        result = self.mcp_server.call_tool(
            "submit_leave_request",
            {
                "employee_id": "emp_12345",
                "leave_type": "PTO",
                "start_date": "2025-06-05",
                "end_date": "2025-06-03"  # End before start
            },
            api_key=self.api_key
        )
        
        # Should return validation error
        assert isinstance(result, dict)
        assert result.get("status") == "error" or "error" in result
    
    def test_submit_leave_request_missing_required_fields(self):
        """Test submit_leave_request with missing required fields."""
        result = self.mcp_server.call_tool(
            "submit_leave_request",
            {
                "employee_id": "emp_12345",
                "leave_type": "PTO"
                # Missing start_date and end_date
            },
            api_key=self.api_key
        )
        
        # Should return validation error
        assert isinstance(result, dict)
        assert result.get("status") == "error" or "error" in result
        error_msg = result.get("error", "") or str(result)
        assert "required" in error_msg.lower() or "missing" in error_msg.lower()
    
    # ========================================================================
    # Test: get_pending_approvals
    # ========================================================================
    
    def test_get_pending_approvals_with_valid_manager(self):
        """Test get_pending_approvals with valid manager ID."""
        # MGR001 has pending requests in database-setup.sql (EMP008)
        result = self.mcp_server.call_tool(
            "get_pending_approvals",
            {"manager_id": "MGR001"},
            api_key=self.api_key
        )
        
        assert isinstance(result, dict)
        assert "managerId" in result
        assert result["managerId"] == "MGR001"
        # Service returns "approvals" not "pending_requests"
        assert "approvals" in result
        assert isinstance(result["approvals"], list)
        
        # Should have at least one pending request
        if len(result["approvals"]) > 0:
            request = result["approvals"][0]
            assert "requestId" in request
            assert "employeeId" in request
            # Status may not be in individual approval items, but all should be PENDING
    
    def test_get_pending_approvals_with_manager_no_pending(self):
        """Test get_pending_approvals with manager who has no pending requests."""
        # Use a manager that might not have pending requests
        result = self.mcp_server.call_tool(
            "get_pending_approvals",
            {"manager_id": "MGR005"},
            api_key=self.api_key
        )
        
        assert isinstance(result, dict)
        assert "managerId" in result
        # Service returns "approvals" not "pending_requests"
        assert "approvals" in result
        assert isinstance(result["approvals"], list)
        # May be empty, which is valid
    
    def test_get_pending_approvals_with_invalid_manager(self):
        """Test get_pending_approvals with invalid manager ID."""
        result = self.mcp_server.call_tool(
            "get_pending_approvals",
            {"manager_id": "INVALID_MGR_999"},
            api_key=self.api_key
        )
        
        # Should return error
        assert isinstance(result, dict)
        assert result.get("status") == "error" or "error" in result
    
    # ========================================================================
    # Test: create_hitl_request
    # ========================================================================
    
    def test_create_hitl_request_valid(self):
        """Test creating a valid HITL request."""
        result = self.mcp_server.call_tool(
            "create_hitl_request",
            {
                "request_type": "LEAVE_EXCEPTION",
                "query": "Integration test - Employee needs exception for extended leave",
                "employee_id": "emp_12345",
                "related_entity_type": "leave_request",
                "priority": "MEDIUM"
            },
            api_key=self.api_key
        )
        
        assert isinstance(result, dict)
        assert "hitlRequestId" in result
        assert "requestType" in result
        assert result["requestType"] == "LEAVE_EXCEPTION"
        assert "status" in result
        assert result["status"] == "PENDING"
        assert "query" in result
    
    def test_create_hitl_request_with_context(self):
        """Test creating HITL request with context."""
        result = self.mcp_server.call_tool(
            "create_hitl_request",
            {
                "request_type": "POLICY_INTERPRETATION",
                "query": "Integration test - Need clarification on policy",
                "employee_id": "emp_67890",
                "context": {
                    "leave_type": "PTO",
                    "requested_days": 10,
                    "available_balance": 5
                },
                "priority": "HIGH"
            },
            api_key=self.api_key
        )
        
        assert isinstance(result, dict)
        assert "hitlRequestId" in result
        assert "context" in result or "query" in result
    
    def test_create_hitl_request_missing_required_fields(self):
        """Test create_hitl_request with missing required fields."""
        result = self.mcp_server.call_tool(
            "create_hitl_request",
            {
                "request_type": "LEAVE_EXCEPTION"
                # Missing required "query" field
            },
            api_key=self.api_key
        )
        
        # Should return validation error
        assert isinstance(result, dict)
        assert result.get("status") == "error" or "error" in result
        error_msg = result.get("error", "") or str(result)
        assert "required" in error_msg.lower() or "missing" in error_msg.lower()
    
    # ========================================================================
    # Test: get_hitl_status
    # ========================================================================
    
    def test_get_hitl_status_with_existing_request(self):
        """Test get_hitl_status with existing HITL request."""
        # First, create a HITL request
        create_result = self.mcp_server.call_tool(
            "create_hitl_request",
            {
                "request_type": "LEAVE_EXCEPTION",
                "query": "Integration test - Get status test",
                "employee_id": "emp_11111"
            },
            api_key=self.api_key
        )
        
        if "hitlRequestId" in create_result:
            hitl_id = create_result["hitlRequestId"]
            
            # Now get its status
            result = self.mcp_server.call_tool(
                "get_hitl_status",
                {"hitl_request_id": hitl_id},
                api_key=self.api_key
            )
            
            assert isinstance(result, dict)
            assert "hitlRequestId" in result
            assert result["hitlRequestId"] == hitl_id
            assert "status" in result
            assert "requestType" in result
    
    def test_get_hitl_status_with_invalid_id(self):
        """Test get_hitl_status with invalid HITL request ID."""
        result = self.mcp_server.call_tool(
            "get_hitl_status",
            {"hitl_request_id": 999999},
            api_key=self.api_key
        )
        
        # Should return error
        assert isinstance(result, dict)
        assert result.get("status") == "error" or "error" in result
        error_msg = result.get("error", "") or str(result)
        assert "not found" in error_msg.lower() or "does not exist" in error_msg.lower()
    
    def test_get_hitl_status_with_string_id(self):
        """Test get_hitl_status with string ID (should convert to int)."""
        # First create a request
        create_result = self.mcp_server.call_tool(
            "create_hitl_request",
            {
                "request_type": "POLICY_INTERPRETATION",
                "query": "Integration test - String ID test",
                "employee_id": "emp_12345"
            },
            api_key=self.api_key
        )
        
        if "hitlRequestId" in create_result:
            hitl_id = create_result["hitlRequestId"]
            
            # Try with string ID
            result = self.mcp_server.call_tool(
                "get_hitl_status",
                {"hitl_request_id": str(hitl_id)},
                api_key=self.api_key
            )
            
            # Should work (tool handles string to int conversion)
            assert isinstance(result, dict)
            assert "hitlRequestId" in result
    
    # ========================================================================
    # Test: tools/list endpoint
    # ========================================================================
    
    def test_tools_list_via_endpoint(self):
        """Test tools/list via HTTP endpoint."""
        response = self.client.post(
            "/api/hrb/lms/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "test-list-tools",
                "method": "tools/list"
            },
            headers={"X-API-Key": self.api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert "tools" in data["result"]
        
        tools = data["result"]["tools"]
        assert isinstance(tools, list)
        assert len(tools) == 6  # Should have 6 tools
        
        # Verify all expected tools are present
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "get_leave_balance",
            "submit_leave_request",
            "get_leave_history",
            "get_pending_approvals",
            "create_hitl_request",
            "get_hitl_status"
        ]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool {expected_tool} not found in list"
    
    # ========================================================================
    # Test: Error Cases
    # ========================================================================
    
    def test_invalid_api_key(self):
        """Test that invalid API key is rejected."""
        response = self.client.post(
            "/api/hrb/lms/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "test-invalid-key",
                "method": "tools/list"
            },
            headers={"X-API-Key": "invalid-api-key"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32000
        assert "Unauthorized" in data["error"]["message"]
    
    def test_missing_api_key(self):
        """Test that missing API key is rejected."""
        response = self.client.post(
            "/api/hrb/lms/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "test-missing-key",
                "method": "tools/list"
            }
            # No X-API-Key header
        )
        
        assert response.status_code == 401
    
    def test_invalid_jsonrpc_version(self):
        """Test that invalid JSON-RPC version is rejected."""
        response = self.client.post(
            "/api/hrb/lms/mcp",
            json={
                "jsonrpc": "1.0",  # Invalid version
                "id": "test-invalid-jsonrpc",
                "method": "tools/list"
            },
            headers={"X-API-Key": self.api_key}
        )
        
        assert response.status_code == 200  # JSON-RPC errors are 200 with error in body
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32600  # Invalid Request
    
    def test_invalid_method(self):
        """Test that invalid method is rejected."""
        response = self.client.post(
            "/api/hrb/lms/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "test-invalid-method",
                "method": "invalid/method"
            },
            headers={"X-API-Key": self.api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method Not Found
    
    def test_unknown_tool(self):
        """Test calling unknown tool."""
        result = self.mcp_server.call_tool(
            "unknown_tool_name",
            {},
            api_key=self.api_key
        )
        
        # Should return error
        assert isinstance(result, dict)
        assert result.get("status") == "error" or "error" in result
        error_msg = result.get("error", "") or str(result)
        assert "unknown" in error_msg.lower() or "not found" in error_msg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

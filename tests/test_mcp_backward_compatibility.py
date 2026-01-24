"""
Tests for MCP server backward compatibility.

This test suite ensures that the refactored MCP implementation maintains
backward compatibility with existing clients and API contracts.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from src.app.api.main import app
from src.app.api.controller.mcp_controller import (
    handle_mcp_request,
    verify_api_key
)
from src.app.api.controller.lms_mcp_server import get_mcp_server, LMSMCPServer
from src.app.api.controller.lms_mcp_tools import tool_registry
from src.app.common.config.config import settings


class TestBackwardCompatibility:
    """Test backward compatibility of refactored MCP implementation."""
    
    def test_list_tools_via_server_works(self):
        """Test that list_tools() via MCP server works."""
        mcp_server = get_mcp_server()
        result = mcp_server.list_tools()
        
        assert isinstance(result, dict)
        assert "tools" in result
        assert isinstance(result["tools"], list)
        assert len(result["tools"]) > 0
        
        # Verify tool structure
        tool = result["tools"][0]
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
    
    def test_call_tool_via_server_works(self):
        """Test that call_tool() via MCP server works."""
        mcp_server = get_mcp_server()
        
        # Mock database session
        with patch('src.app.api.controller.lms_mcp_server.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            
            # Mock service
            with patch('src.app.api.controller.lms_mcp_tools.LeaveBalanceService') as mock_service_class:
                mock_service = MagicMock()
                mock_service.get_leave_balance.return_value = {
                    "employeeId": "EMP001",
                    "year": 2025,
                    "balances": []
                }
                mock_service_class.return_value = mock_service
                
                result = mcp_server.call_tool(
                    "get_leave_balance",
                    {"employee_id": "EMP001", "year": 2025},
                    api_key=settings.api_key
                )
                
                assert isinstance(result, dict)
                assert "employeeId" in result or "error" in result
    
    def test_mcp_endpoint_still_works(self):
        """Test that MCP endpoint still works with old request format."""
        client = TestClient(app)
        
        # Test tools/list
        response = client.post(
            "/api/hrb/lms/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "test-1",
                "method": "tools/list"
            },
            headers={"X-API-Key": settings.api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test-1"
        assert "result" in data
        assert "tools" in data["result"]
    
    def test_mcp_endpoint_tool_call_still_works(self):
        """Test that MCP endpoint tool call still works."""
        client = TestClient(app)
        
        # Mock database and service
        with patch('src.app.api.controller.lms_mcp_server.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            
            with patch('src.app.api.controller.lms_mcp_tools.LeaveBalanceService') as mock_service_class:
                mock_service = MagicMock()
                mock_service.get_leave_balance.return_value = {
                    "employeeId": "EMP001",
                    "year": 2025,
                    "balances": []
                }
                mock_service_class.return_value = mock_service
                
                response = client.post(
                    "/api/hrb/lms/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": "test-2",
                        "method": "tools/call",
                        "params": {
                            "name": "get_leave_balance",
                            "arguments": {
                                "employee_id": "EMP001",
                                "year": 2025
                            }
                        }
                    },
                    headers={"X-API-Key": settings.api_key}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["jsonrpc"] == "2.0"
                assert data["id"] == "test-2"
                assert "result" in data or "error" in data
    
    def test_api_key_validation_still_works(self):
        """Test that API key validation still works at endpoint level."""
        client = TestClient(app)
        
        # Test without API key
        response = client.post(
            "/api/hrb/lms/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "test-3",
                "method": "tools/list"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == -32000
        assert "Unauthorized" in data["error"]["message"]
    
    def test_tool_schema_format_unchanged(self):
        """Test that tool schema format matches MCP standard."""
        mcp_server = get_mcp_server()
        tools = mcp_server.list_tools()
        
        for tool in tools["tools"]:
            # MCP standard uses "inputSchema" (camelCase)
            assert "inputSchema" in tool, f"Tool {tool.get('name')} missing inputSchema"
            assert "name" in tool
            assert "description" in tool
            
            # Verify inputSchema structure
            schema = tool["inputSchema"]
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance."""
    
    def test_jsonrpc_version_in_response(self):
        """Test that JSON-RPC 2.0 version is in all responses."""
        client = TestClient(app)
        
        response = client.post(
            "/api/hrb/lms/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "test-4",
                "method": "tools/list"
            },
            headers={"X-API-Key": settings.api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
    
    def test_mcp_protocol_headers(self):
        """Test that MCP protocol headers are present in responses."""
        client = TestClient(app)
        
        response = client.post(
            "/api/hrb/lms/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "test-5",
                "method": "tools/list"
            },
            headers={"X-API-Key": settings.api_key}
        )
        
        assert response.status_code == 200
        assert "X-MCP-Version" in response.headers
        assert "X-MCP-Transport" in response.headers
        assert "X-MCP-JSONRPC-Version" in response.headers
        assert response.headers["X-MCP-Version"] == "1.0"
        assert response.headers["X-MCP-Transport"] == "http"
        assert response.headers["X-MCP-JSONRPC-Version"] == "2.0"
    
    def test_jsonrpc_error_codes(self):
        """Test that JSON-RPC 2.0 error codes are used correctly."""
        client = TestClient(app)
        
        # Test invalid method
        response = client.post(
            "/api/hrb/lms/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "test-6",
                "method": "invalid_method"
            },
            headers={"X-API-Key": settings.api_key}
        )
        
        assert response.status_code == 200  # JSON-RPC errors are 200 with error in body
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method Not Found
        assert data["error"]["message"] == "Method Not Found"
    
    def test_tool_not_found_error(self):
        """Test error handling for unknown tool."""
        client = TestClient(app)
        
        with patch('src.app.api.controller.lms_mcp_server.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            
            response = client.post(
                "/api/hrb/lms/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "test-7",
                    "method": "tools/call",
                    "params": {
                        "name": "unknown_tool",
                        "arguments": {}
                    }
                },
                headers={"X-API-Key": settings.api_key}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            result = data["result"]
            assert "error" in result
            assert result["status"] == "error"
            assert result["error_type"] == "tool_not_found"


class TestToolLevelAPIKeyValidation:
    """Test tool-level API key validation."""
    
    def test_tool_level_api_key_validation_works(self):
        """Test that tool-level API key validation is enforced."""
        server = get_mcp_server()
        
        # Test with no API key (should fail for tools that require it)
        with patch('src.app.api.controller.lms_mcp_server.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            
            result = server.call_tool(
                "get_leave_balance",
                {"employee_id": "EMP001"},
                api_key=None
            )
            
            assert isinstance(result, dict)
            assert result.get("status") == "error"
            assert result.get("error_type") == "authentication_error"
            assert "API key required" in result.get("error", "")
    
    def test_tool_level_api_key_validation_with_invalid_key(self):
        """Test that invalid API key is rejected at tool level."""
        server = get_mcp_server()
        
        with patch('src.app.api.controller.lms_mcp_server.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            
            result = server.call_tool(
                "get_leave_balance",
                {"employee_id": "EMP001"},
                api_key="invalid_key"
            )
            
            assert isinstance(result, dict)
            assert result.get("status") == "error"
            assert result.get("error_type") == "authentication_error"
            assert "Invalid API key" in result.get("error", "")
    
    def test_tool_level_api_key_validation_with_valid_key(self):
        """Test that valid API key passes tool-level validation."""
        server = get_mcp_server()
        
        with patch('src.app.api.controller.lms_mcp_server.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            
            with patch('src.app.api.controller.lms_mcp_tools.LeaveBalanceService') as mock_service_class:
                mock_service = MagicMock()
                mock_service.get_leave_balance.return_value = {
                    "employeeId": "EMP001",
                    "year": 2025,
                    "balances": []
                }
                mock_service_class.return_value = mock_service
                
                result = server.call_tool(
                    "get_leave_balance",
                    {"employee_id": "EMP001", "year": 2025},
                    api_key=settings.api_key
                )
                
                # Should not have authentication error
                assert result.get("error_type") != "authentication_error"
                # Should have result or business error, not auth error
                if "error" in result:
                    assert "API key" not in result.get("error", "")


class TestMCPToolRegistry:
    """Test MCP tool registry functionality."""
    
    def test_all_tools_registered(self):
        """Test that all expected tools are registered."""
        tools = tool_registry.list_tools()
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
            assert expected_tool in tool_names, f"Tool {expected_tool} not registered"
    
    def test_tool_schema_completeness(self):
        """Test that all tools have complete schemas."""
        tools = tool_registry.list_tools()
        
        for tool in tools:
            schema = tool["inputSchema"]
            assert "type" in schema
            assert "properties" in schema
            assert "required" in schema
            
            # Verify properties match required fields
            properties = schema["properties"]
            required = schema["required"]
            
            for req_field in required:
                assert req_field in properties, f"Required field {req_field} missing from properties"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for the MCP registry functionality.
"""

import os
import json
import tempfile
import pytest
from erasmus.mcp.mcp import MCPRegistry, McpError


@pytest.fixture
def temp_registry_file():
    """Create a temporary registry file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        yield temp_file.name
    # Clean up the temporary file after tests
    os.unlink(temp_file.name)


@pytest.fixture
def registry(temp_registry_file):
    """Create a registry instance with a temporary file."""
    return MCPRegistry(registry_file=temp_registry_file)


def test_register_server(registry):
    """Test registering a server."""
    registry.register_server("test-server", "localhost", 8000)
    server = registry.get_server("test-server")
    assert server["host"] == "localhost"
    assert server["port"] == 8000


def test_register_duplicate_server(registry):
    """Test registering a duplicate server."""
    registry.register_server("test-server", "localhost", 8000)
    with pytest.raises(McpError, match="Server 'test-server' already registered"):
        registry.register_server("test-server", "localhost", 8001)


def test_unregister_server(registry):
    """Test unregistering a server."""
    registry.register_server("test-server", "localhost", 8000)
    registry.unregister_server("test-server")
    with pytest.raises(McpError, match="Server 'test-server' not found"):
        registry.get_server("test-server")


def test_unregister_nonexistent_server(registry):
    """Test unregistering a nonexistent server."""
    with pytest.raises(McpError, match="Server 'nonexistent-server' not found"):
        registry.unregister_server("nonexistent-server")


def test_list_servers(registry):
    """Test listing servers."""
    registry.register_server("server1", "localhost", 8000)
    registry.register_server("server2", "localhost", 8001)
    servers = registry.list_servers()
    assert "server1" in servers
    assert "server2" in servers
    assert len(servers) == 2


def test_register_client(registry):
    """Test registering a client."""
    registry.register_server("test-server", "localhost", 8000)
    registry.register_client("test-client", "test-server")
    client = registry.get_client("test-client")
    assert client["server"] == "test-server"


def test_register_client_nonexistent_server(registry):
    """Test registering a client to a nonexistent server."""
    with pytest.raises(McpError, match="Server 'nonexistent-server' not found"):
        registry.register_client("test-client", "nonexistent-server")


def test_register_duplicate_client(registry):
    """Test registering a duplicate client."""
    registry.register_server("test-server", "localhost", 8000)
    registry.register_client("test-client", "test-server")
    with pytest.raises(McpError, match="Client 'test-client' already registered"):
        registry.register_client("test-client", "test-server")


def test_unregister_client(registry):
    """Test unregistering a client."""
    registry.register_server("test-server", "localhost", 8000)
    registry.register_client("test-client", "test-server")
    registry.unregister_client("test-client")
    with pytest.raises(McpError, match="Client 'test-client' not found"):
        registry.get_client("test-client")


def test_unregister_nonexistent_client(registry):
    """Test unregistering a nonexistent client."""
    with pytest.raises(McpError, match="Client 'nonexistent-client' not found"):
        registry.unregister_client("nonexistent-client")


def test_list_clients(registry):
    """Test listing clients."""
    registry.register_server("test-server", "localhost", 8000)
    registry.register_client("client1", "test-server")
    registry.register_client("client2", "test-server")
    clients = registry.list_clients()
    assert "client1" in clients
    assert "client2" in clients
    assert len(clients) == 2


def test_persistence(registry, temp_registry_file):
    """Test that registry data persists between instances."""
    registry.register_server("test-server", "localhost", 8000)
    registry.register_client("test-client", "test-server")

    # Create a new registry instance with the same file
    new_registry = MCPRegistry(registry_file=temp_registry_file)

    # Check that the data was loaded correctly
    server = new_registry.get_server("test-server")
    assert server["host"] == "localhost"
    assert server["port"] == 8000

    client = new_registry.get_client("test-client")
    assert client["server"] == "test-server"

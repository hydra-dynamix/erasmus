import os
import pytest
from pathlib import Path
from erasmus.protocol import ProtocolManager, ProtocolError


@pytest.fixture
def protocol_manager(tmp_path):
    """Create a ProtocolManager instance with temporary directories."""
    base_dir = tmp_path / "templates" / "protocols"
    user_dir = tmp_path / "protocols"
    return ProtocolManager(base_dir=str(base_dir), user_dir=str(user_dir))


@pytest.fixture
def sample_protocol_files(tmp_path):
    """Create sample protocol files for testing."""
    protocol_dir = tmp_path / "test_protocol"
    protocol_dir.mkdir()

    # Create sample protocol file
    protocol_file = protocol_dir / "test_protocol.xml"
    protocol_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<Protocol>
    <Name>Test Protocol</Name>
    <Description>Test protocol description</Description>
    <Steps>
        <Step>Test step 1</Step>
        <Step>Test step 2</Step>
    </Steps>
</Protocol>""")

    return protocol_dir


def test_create_protocol(protocol_manager):
    """Test creating a protocol."""
    protocol_name = "test_protocol"
    content = "<Protocol><Test>Test content</Test></Protocol>"
    protocol = protocol_manager.create_protocol(protocol_name, content)
    assert protocol.name == "test_protocol"
    assert protocol.content == content


def test_create_duplicate_protocol(protocol_manager):
    """Test creating a protocol that already exists."""
    protocol_name = "duplicate_protocol"
    content = "<Protocol><Test>Test content</Test></Protocol>"
    protocol_manager.create_protocol(protocol_name, content)
    with pytest.raises(FileExistsError):
        protocol_manager.create_protocol(protocol_name, content)


def test_delete_protocol(protocol_manager):
    """Test deleting a protocol."""
    protocol_name = "delete_protocol"
    content = "<Protocol><Test>Test content</Test></Protocol>"
    protocol_manager.create_protocol(protocol_name, content)
    protocol_manager.delete_protocol(protocol_name)
    assert protocol_manager.get_protocol(protocol_name) is None


def test_delete_nonexistent_protocol(protocol_manager):
    """Test deleting a nonexistent protocol."""
    with pytest.raises(FileNotFoundError):
        protocol_manager.delete_protocol("nonexistent")


def test_list_protocols(protocol_manager):
    """Test listing protocols."""
    protocol_names = ["protocol1", "protocol2", "protocol3"]
    content = "<Protocol><Test>Test content</Test></Protocol>"
    for name in protocol_names:
        protocol_manager.create_protocol(name, content)
    protocols = protocol_manager.list_protocols()
    assert all(name in protocols for name in protocol_names)


def test_get_protocol(protocol_manager):
    """Test getting a protocol."""
    protocol_name = "test_protocol"
    content = "<Protocol><Test>Test content</Test></Protocol>"
    created_protocol = protocol_manager.create_protocol(protocol_name, content)
    retrieved_protocol = protocol_manager.get_protocol(protocol_name)
    assert retrieved_protocol is not None
    assert retrieved_protocol.name == created_protocol.name
    assert retrieved_protocol.content == created_protocol.content


def test_get_nonexistent_protocol(protocol_manager):
    """Test getting a nonexistent protocol."""
    assert protocol_manager.get_protocol("nonexistent") is None


def test_update_protocol(protocol_manager):
    """Test updating a protocol."""
    protocol_name = "test_protocol"
    content = "<Protocol><Test>Test content</Test></Protocol>"
    protocol_manager.create_protocol(protocol_name, content)
    new_content = "<Protocol><Test>Updated content</Test></Protocol>"
    updated_protocol = protocol_manager.update_protocol(protocol_name, new_content)
    assert updated_protocol.content == new_content


def test_update_nonexistent_protocol(protocol_manager):
    """Test updating a nonexistent protocol."""
    with pytest.raises(FileNotFoundError):
        protocol_manager.update_protocol("nonexistent", "<Protocol></Protocol>")


def test_invalid_xml_content(protocol_manager):
    """Test handling invalid XML content."""
    protocol_name = "invalid_protocol"
    content = "Invalid XML content"
    protocol = protocol_manager.create_protocol(protocol_name, content)
    assert "<Protocol>" in protocol.content
    assert "Invalid XML content" in protocol.content


def test_sanitize_name(protocol_manager):
    """Test protocol name sanitization."""
    protocol_name = "test*protocol"
    content = "<Protocol><Test>Test content</Test></Protocol>"
    protocol = protocol_manager.create_protocol(protocol_name, content)
    assert protocol.name == "test_protocol"

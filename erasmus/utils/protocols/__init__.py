"""Protocol system for Erasmus.

This package provides a protocol system for managing agent workflows within the Erasmus framework.
"""

from .base import Protocol, ProtocolArtifact, ProtocolTransition
from .manager import ProtocolManager, ProtocolRegistry
from .server import ProtocolServer, ProtocolExecutionRequest, ProtocolExecutionResponse
from .integration import ProtocolIntegration
from .cli import add_protocol_commands, handle_protocol_commands, update_context_with_protocol

__all__ = [
    "Protocol",
    "ProtocolArtifact",
    "ProtocolTransition",
    "ProtocolManager",
    "ProtocolRegistry",
    "ProtocolServer",
    "ProtocolExecutionRequest",
    "ProtocolExecutionResponse",
    "ProtocolIntegration",
    "add_protocol_commands",
    "handle_protocol_commands",
    "update_context_with_protocol",
]

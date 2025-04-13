from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
from pathlib import Path

from erasmus.utils.logging import get_logger
from erasmus.utils.paths import SetupPaths
from .manager import ProtocolManager
from .base import Protocol, ProtocolArtifact, ProtocolTransition

logger = logging.getLogger(__name__)


class ProtocolExecutionRequest(BaseModel):
    """Request model for protocol execution."""

    protocol_name: str
    context: dict


class ProtocolExecutionResponse(BaseModel):
    """Response model for protocol execution."""

    artifacts: List[ProtocolArtifact]
    next_transitions: List[ProtocolTransition]


class ProtocolServer:
    """Server for managing protocol execution and transitions."""

    def __init__(self, setup_paths: Optional[SetupPaths] = None):
        """Initialize the protocol server."""
        self.setup_paths = setup_paths or SetupPaths.with_project_root(Path.cwd())
        self.protocol_manager = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> None:
        """Initialize the protocol server."""
        self.protocol_manager = await ProtocolManager.create()
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default event handlers."""
        self.protocol_manager.register_event_handler(
            "protocol_activated", self._handle_protocol_activated
        )
        self.protocol_manager.register_event_handler(
            "protocol_completed", self._handle_protocol_completed
        )
        self.protocol_manager.register_event_handler(
            "transition_triggered", self._handle_transition
        )
        self.protocol_manager.register_event_handler("artifact_produced", self._handle_artifact)

    def _handle_protocol_activated(self, data: Dict[str, Any]) -> None:
        """Handle protocol activation event."""
        protocol_name = data.get("protocol_name")
        self.logger.info(f"Protocol activated: {protocol_name}")

    def _handle_protocol_completed(self, data: Dict[str, Any]) -> None:
        """Handle protocol completion event."""
        protocol_name = data.get("protocol_name")
        self.logger.info(f"Protocol completed: {protocol_name}")

    def _handle_transition(self, data: Dict[str, Any]) -> None:
        """Handle transition event."""
        from_protocol = data.get("from_protocol")
        to_protocol = data.get("to_protocol")
        self.logger.info(f"Transition: {from_protocol} -> {to_protocol}")

    def _handle_artifact(self, data: Dict[str, Any]) -> None:
        """Handle artifact production event."""
        protocol_name = data.get("protocol_name")
        artifact_type = data.get("artifact_type")
        self.logger.info(f"Artifact produced: {artifact_type} from {protocol_name}")

    async def execute_protocol(
        self, protocol_name: str, context: Dict[str, Any]
    ) -> List[ProtocolArtifact]:
        """Execute a protocol with the given context."""
        if not self.protocol_manager:
            await self.initialize()

        protocol = self.protocol_manager.get_protocol(protocol_name)
        if not protocol:
            raise ValueError(f"Protocol not found: {protocol_name}")

        await self.protocol_manager.activate_protocol(protocol_name)
        artifacts = await self.protocol_manager.execute_protocol(protocol_name, context)
        await self.protocol_manager.complete_protocol(protocol_name, {"artifacts": artifacts})
        return artifacts

    def get_protocol(self, protocol_name: str) -> Optional[Protocol]:
        """Get a protocol by name."""
        return self.protocol_manager.get_protocol(protocol_name) if self.protocol_manager else None

    def list_protocols(self) -> List[Protocol]:
        """List all available protocols."""
        return self.protocol_manager.list_protocols() if self.protocol_manager else []

    def get_protocol_transitions(
        self, protocol_name: str, context: Dict[str, Any]
    ) -> List[ProtocolTransition]:
        """Get available transitions for a protocol."""
        return (
            self.protocol_manager.get_protocol_transitions(protocol_name, context)
            if self.protocol_manager
            else []
        )

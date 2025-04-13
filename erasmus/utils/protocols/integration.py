from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

from erasmus.utils.logging import get_logger
from erasmus.utils.paths import SetupPaths
from .base import Protocol, ProtocolArtifact, ProtocolTransition
from .manager import ProtocolManager
from .server import ProtocolServer
from .context import Context

logger = get_logger(__name__)


class ProtocolIntegration:
    """Integration layer for the protocol system."""

    def __init__(self, setup_paths: SetupPaths = None):
        """Initialize the protocol integration.

        Args:
            setup_paths: Optional SetupPaths instance. If not provided, will create one with current directory.
        """
        self.protocol_server = None
        self.setup_paths = setup_paths or SetupPaths.with_project_root(Path.cwd())
        self.registry_path = self.setup_paths.protocols_dir / "agent_registry.json"
        self.current_protocol = None
        self.context = Context()
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default event handlers."""
        self._handlers = {
            "protocol_activated": self._handle_protocol_activated,
            "protocol_completed": self._handle_protocol_completed,
            "transition": self._handle_transition,
            "artifact": self._handle_artifact,
        }

    def _handle_protocol_activated(self, data: Dict[str, Any]):
        """Handle protocol activation event."""
        logger.info(f"Protocol activated: {data['protocol']}")
        self.current_protocol = data["protocol"]
        self.context.active_protocol = data["protocol"]

    def _handle_protocol_completed(self, data: Dict[str, Any]):
        """Handle protocol completion event."""
        logger.info(f"Protocol completed: {data['protocol']}")
        self.current_protocol = None
        self.context.active_protocol = None

    def _handle_transition(self, data: Dict[str, Any]):
        """Handle transition event."""
        logger.info(f"Transition: {data['from_protocol']} -> {data['to_protocol']}")
        self.current_protocol = data["to_protocol"]
        self.context.active_protocol = data["to_protocol"]

    def _handle_artifact(self, data: Dict[str, Any]):
        """Handle artifact event."""
        logger.info(f"Artifact produced: {data['artifact'].name}")
        self.context.protocol_artifacts[data["artifact"].name] = data["artifact"].content

    async def initialize(self) -> None:
        """Initialize the protocol system."""
        if not self.registry_path.exists():
            logger.error(f"Registry file not found: {self.registry_path}")
            return

        self.protocol_server = ProtocolServer(self.registry_path)
        logger.info("Protocol system initialized")

    def register_protocol_prompts(self) -> None:
        """Register prompt functions for protocols."""
        if not self.protocol_server:
            logger.error("Protocol server not initialized")
            return

        # Register default prompt functions
        self.protocol_server.protocol_manager.register_default_prompts()
        logger.info("Protocol prompts registered")

    async def execute_protocol(
        self, protocol_name: str, context: Dict[str, Any]
    ) -> List[ProtocolArtifact]:
        """Execute a protocol with the given context."""
        if not self.protocol_server:
            logger.error("Protocol server not initialized")
            return []

        try:
            # Manually trigger protocol activation
            self._handle_protocol_activated({"protocol": protocol_name})

            artifacts = await self.protocol_server.execute_protocol(protocol_name, context)

            # Write file artifacts to disk
            for artifact in artifacts:
                if artifact.type == "file":
                    artifact_path = self.setup_paths.protocols_dir / "stored" / artifact.name
                    artifact_path.write_text(artifact.content)
                    logger.info(f"Wrote artifact to {artifact_path}")

            # Manually trigger protocol completion
            self._handle_protocol_completed({"protocol": protocol_name})

            return artifacts
        except Exception as e:
            logger.error(f"Error executing protocol {protocol_name}: {e}")
            return []

    def get_protocol(self, protocol_name: str) -> Optional[Protocol]:
        """Get a protocol by name."""
        if not self.protocol_server:
            logger.error("Protocol server not initialized")
            return None

        return self.protocol_server.get_protocol(protocol_name)

    def list_protocols(self) -> List[str]:
        """List all available protocols."""
        if not self.protocol_server:
            logger.error("Protocol server not initialized")
            return []

        return self.protocol_server.list_protocols()

    def get_protocol_transitions(
        self, protocol_name: str, context: Dict[str, Any]
    ) -> List[ProtocolTransition]:
        """Get available transitions for a protocol based on context."""
        if not self.protocol_server:
            logger.error("Protocol server not initialized")
            return []

        return self.protocol_server.get_protocol_transitions(protocol_name, context)

    async def transition_to_protocol(
        self, from_protocol: str, to_protocol: str, context: Dict[str, Any]
    ) -> bool:
        """Manually transition from one protocol to another."""
        if not self.protocol_server:
            logger.error("Protocol server not initialized")
            return False

        try:
            # Verify the transition is valid
            transitions = self.get_protocol_transitions(from_protocol, context)
            valid_transition = any(t.to_protocol == to_protocol for t in transitions)

            if not valid_transition:
                logger.error(f"Invalid transition from {from_protocol} to {to_protocol}")
                return False

            # Manually trigger the transition
            self._handle_transition({"from_protocol": from_protocol, "to_protocol": to_protocol})

            return True
        except Exception as e:
            logger.error(f"Error transitioning from {from_protocol} to {to_protocol}: {e}")
            return False

    async def run_workflow(
        self, start_protocol: str, context: Dict[str, Any]
    ) -> List[ProtocolArtifact]:
        """Run a workflow starting from a specific protocol."""
        if not self.protocol_server:
            logger.error("Protocol server not initialized")
            return []

        try:
            artifacts = []
            current_protocol = start_protocol

            while current_protocol:
                # Execute current protocol
                protocol_artifacts = await self.execute_protocol(current_protocol, context)
                artifacts.extend(protocol_artifacts)

                # Get next transitions
                transitions = self.get_protocol_transitions(current_protocol, context)
                if not transitions:
                    break

                # Select first transition and manually transition
                next_protocol = transitions[0].to_protocol
                success = await self.transition_to_protocol(
                    current_protocol, next_protocol, context
                )
                if not success:
                    break

                current_protocol = next_protocol

            return artifacts
        except Exception as e:
            logger.error(f"Error running workflow from {start_protocol}: {e}")
            return []

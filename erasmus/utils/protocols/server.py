from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from erasmus.utils.logging import get_logger
from .manager import ProtocolManager
from .base import Protocol, ProtocolArtifact, ProtocolTransition

logger = get_logger(__name__)


class ProtocolExecutionRequest(BaseModel):
    """Request model for protocol execution."""

    protocol_name: str
    context: dict


class ProtocolExecutionResponse(BaseModel):
    """Response model for protocol execution."""

    artifacts: List[ProtocolArtifact]
    next_transitions: List[ProtocolTransition]


class ProtocolServer:
    """Server integration for the protocol system."""

    def __init__(self):
        self.protocol_manager = ProtocolManager()

    async def initialize(self, registry_path: str) -> None:
        """Initialize the protocol system."""
        await self.protocol_manager.load_registry(registry_path)
        logger.info(f"Protocol server initialized with registry: {registry_path}")

    def register_prompt_function(self, protocol_name: str, prompt_function: callable) -> None:
        """Register a prompt function for a protocol."""
        self.protocol_manager.register_prompt_function(protocol_name, prompt_function)

    def list_protocols(self) -> List[Protocol]:
        """List all available protocols."""
        return self.protocol_manager.list_protocols()

    def get_protocol(self, name: str) -> Optional[Protocol]:
        """Get a specific protocol by name."""
        return self.protocol_manager.get_protocol(name)

    async def execute_protocol(
        self, name: str, context: Dict[str, Any]
    ) -> ProtocolExecutionResponse:
        """Execute a protocol with given context."""
        try:
            # Execute the protocol
            artifacts = await self.protocol_manager.get_protocol(name).execute(context)

            # Get possible next transitions
            next_transitions = await self.protocol_manager.execute_protocol(name, context)

            return ProtocolExecutionResponse(artifacts=artifacts, next_transitions=next_transitions)
        except Exception as e:
            logger.error(f"Error executing protocol {name}: {e}")
            raise

    def get_protocol_transitions(
        self, name: str, direction: str = "from"
    ) -> List[ProtocolTransition]:
        """Get transitions for a protocol."""
        if direction == "from":
            return self.protocol_manager.get_transitions_from(name)
        elif direction == "to":
            return self.protocol_manager.get_transitions_to(name)
        else:
            raise ValueError("Invalid direction")

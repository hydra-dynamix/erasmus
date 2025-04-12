import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

from pydantic import BaseModel

from erasmus.utils.logging import get_logger
from .base import Protocol, ProtocolTransition

logger = get_logger(__name__)


class ProtocolRegistry(BaseModel):
    """Registry containing all protocols and their transitions."""

    agents: List[Protocol]
    workflow_transitions: List[ProtocolTransition]


class ProtocolManager:
    """Manages protocol loading, registration, and execution."""

    def __init__(self):
        self.protocols: Dict[str, Protocol] = {}
        self.transitions: List[ProtocolTransition] = []
        self.prompt_functions: Dict[str, Callable[[dict], Any]] = {}

    async def load_registry(self, registry_path: str) -> None:
        """Load protocols from a registry file."""
        if not os.path.exists(registry_path):
            raise FileNotFoundError(f"Registry file not found: {registry_path}")

        with open(registry_path, "r") as f:
            data = json.load(f)

        registry = ProtocolRegistry(**data)

        # Load each protocol
        for agent in registry.agents:
            protocol = Protocol(
                name=agent.name,
                role=agent.role,
                file_path=agent.file_path,
                triggers=agent.triggers,
                produces=agent.produces,
                consumes=agent.consumes,
            )

            # Check if we have a prompt function for this protocol
            if protocol.name in self.prompt_functions:
                protocol.prompt = self.prompt_functions[protocol.name]
            else:
                logger.warning(f"No prompt function registered for protocol: {protocol.name}")

            self.protocols[protocol.name] = protocol

        # Load transitions
        self.transitions = registry.workflow_transitions
        logger.info(
            f"Loaded {len(self.protocols)} protocols and {len(self.transitions)} transitions"
        )

    def register_prompt_function(
        self, protocol_name: str, prompt_function: Callable[[dict], Any]
    ) -> None:
        """Register a prompt function for a protocol."""
        self.prompt_functions[protocol_name] = prompt_function
        logger.info(f"Registered prompt function for protocol: {protocol_name}")

        # Update the protocol if it exists
        if protocol_name in self.protocols:
            self.protocols[protocol_name].prompt = prompt_function

    def get_protocol(self, name: str) -> Optional[Protocol]:
        """Get a protocol by name."""
        return self.protocols.get(name)

    def list_protocols(self) -> List[Protocol]:
        """List all registered protocols."""
        return list(self.protocols.values())

    def get_transitions_from(self, protocol_name: str) -> List[ProtocolTransition]:
        """Get all transitions originating from a protocol."""
        return [t for t in self.transitions if t.from_agent == protocol_name]

    def get_transitions_to(self, protocol_name: str) -> List[ProtocolTransition]:
        """Get all transitions targeting a protocol."""
        return [t for t in self.transitions if t.to_agent == protocol_name]

    async def execute_protocol(self, name: str, context: dict) -> List[ProtocolTransition]:
        """Execute a protocol and return possible next transitions."""
        protocol = self.get_protocol(name)
        if not protocol:
            raise ValueError(f"Protocol not found: {name}")

        # Execute the protocol
        artifacts = await protocol.execute(context)

        # Find possible next transitions based on produced artifacts
        possible_transitions = []
        for artifact in artifacts:
            transitions = [
                t
                for t in self.transitions
                if t.from_agent == protocol.name and t.artifact == artifact.name
            ]
            possible_transitions.extend(transitions)

        return possible_transitions

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Set

from pydantic import BaseModel, Field

from erasmus.utils.logging import get_logger
from erasmus.utils.paths import SetupPaths
from .base import Protocol, ProtocolTransition, ProtocolArtifact

logger = get_logger(__name__)


class ProtocolRegistry(BaseModel):
    """Registry containing all protocols and their transitions."""

    agents: List[Protocol] = Field(default_factory=list)
    workflow_transitions: List[ProtocolTransition] = Field(default_factory=list)


class ProtocolManager(BaseModel):
    """Manages protocol loading, registration, and execution."""

    protocols: Dict[str, Protocol] = Field(default_factory=dict)
    prompt_functions: Dict[str, Callable] = Field(default_factory=dict)
    event_handlers: Dict[str, List[Callable]] = Field(default_factory=dict)
    setup_paths: SetupPaths = Field(
        default_factory=lambda: SetupPaths.with_project_root(Path.cwd())
    )

    @classmethod
    async def create(cls) -> "ProtocolManager":
        """Create a new ProtocolManager instance."""
        instance = cls()
        await instance.load_registry()
        return instance

    async def load_registry(self) -> None:
        """Load the protocol registry from the registry file."""
        registry_path = self.setup_paths.protocols_dir / "agent_registry.json"
        if not registry_path.exists():
            logger.error(f"Registry file not found: {registry_path}")
            return

        try:
            with open(registry_path, "r") as f:
                registry_data = json.load(f)

            for agent in registry_data.get("agents", []):
                protocol = Protocol(
                    name=agent["name"],
                    role=agent["role"],
                    triggers=agent.get("triggers", []),
                    produces=agent.get("produces", []),
                    consumes=agent.get("consumes", []),
                    file_path=Path(agent["file_path"]),
                )
                self.protocols[protocol.name] = protocol
                logger.info(f"Loaded protocol: {protocol.name}")

        except Exception as e:
            logger.error(f"Error loading registry: {e}")

    def register_prompt_function(self, protocol_name: str, prompt_function: Callable) -> None:
        """Register a prompt function for a protocol."""
        if protocol_name not in self.protocols:
            logger.warning(f"Cannot register prompt function for unknown protocol: {protocol_name}")
            return

        self.prompt_functions[protocol_name] = prompt_function
        logger.info(f"Registered prompt function for protocol: {protocol_name}")

    def register_default_prompts(self) -> None:
        """Register default prompt functions for all protocols."""

        def product_owner_prompt(context: Dict[str, Any]) -> str:
            return f"""# Project Architecture and Progress

## Architecture
{context.get("architecture", "No architecture document available.")}

## Progress
{context.get("progress", "No progress document available.")}

## Tasks
{context.get("tasks", "No tasks document available.")}
"""

        # Register the default prompt for the Product Owner Agent
        self.register_prompt_function("Product Owner Agent", product_owner_prompt)
        logger.info("Registered default prompt functions")

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register an event handler for a specific event type."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for event: {event_type}")

    async def _emit_event(self, event_type: str, data: Any) -> None:
        """Emit an event to all registered handlers."""
        if event_type not in self.event_handlers:
            return

        for handler in self.event_handlers[event_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in {event_type} event handler: {e}")

    async def execute_protocol_with_context(
        self, protocol_name: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a protocol with the given context."""
        if protocol_name not in self.protocols:
            raise ValueError(f"Unknown protocol: {protocol_name}")

        protocol = self.protocols[protocol_name]
        prompt_function = self.prompt_functions.get(protocol_name)

        if not prompt_function:
            raise ValueError(f"No prompt function registered for protocol: {protocol_name}")

        # Emit protocol activated event
        await self._emit_event("protocol_activated", {"protocol": protocol, "context": context})

        # Execute the protocol
        try:
            result = await prompt_function(context)
            await self._emit_event("protocol_completed", {"protocol": protocol, "result": result})
            return result
        except Exception as e:
            logger.error(f"Error executing protocol {protocol_name}: {e}")
            raise

    def get_protocol(self, protocol_name: str) -> Optional[Protocol]:
        """Get a protocol by name."""
        return self.protocols.get(protocol_name)

    def list_protocols(self) -> List[Protocol]:
        """List all available protocols."""
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

    async def initialize(self) -> None:
        """Initialize the protocol manager."""
        await self.load_registry()
        self.protocols = self.registry.protocols

    def _trigger_event(self, event_type: str, **kwargs) -> None:
        """Trigger an event with the given parameters.

        Args:
            event_type: Type of event to trigger
            **kwargs: Event parameters
        """
        if event_type not in self.event_handlers:
            return

        for handler in self.event_handlers[event_type]:
            try:
                handler(**kwargs)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")

    async def activate_protocol(self, protocol_name: str) -> bool:
        """Activate a protocol and trigger appropriate events.

        Args:
            protocol_name: Name of the protocol to activate

        Returns:
            bool: True if protocol was activated successfully
        """
        if protocol_name not in self.protocols:
            logger.error(f"Protocol not found: {protocol_name}")
            return False

        protocol = self.protocols[protocol_name]
        self._trigger_event("protocol_activated", protocol=protocol)
        return True

    async def complete_protocol(self, protocol_name: str, artifacts: Dict[str, Any]) -> bool:
        """Complete a protocol and trigger appropriate events.

        Args:
            protocol_name: Name of the protocol that completed
            artifacts: Artifacts produced by the protocol

        Returns:
            bool: True if protocol was completed successfully
        """
        if protocol_name not in self.protocols:
            logger.error(f"Protocol not found: {protocol_name}")
            return False

        protocol = self.protocols[protocol_name]

        # Trigger artifact produced events
        for artifact_name, artifact_value in artifacts.items():
            self._trigger_event(
                "artifact_produced",
                protocol=protocol,
                artifact_name=artifact_name,
                artifact_value=artifact_value,
            )

            # Check for transitions triggered by this artifact
            transitions = self.registry.get_transitions_for_artifact(protocol_name, artifact_name)
            for transition in transitions:
                self._trigger_event(
                    "transition_triggered",
                    from_protocol=protocol,
                    to_protocol=self.protocols[transition.to_agent],
                    trigger=transition.trigger,
                    artifact=artifact_name,
                )

        # Trigger protocol completed event
        self._trigger_event("protocol_completed", protocol=protocol, artifacts=artifacts)
        return True

    def get_transitions(self, protocol_name: str) -> List[ProtocolTransition]:
        """Get all transitions for a protocol."""
        return self.registry.get_transitions(protocol_name)

    def get_protocol_transitions(
        self, protocol_name: str, context: Dict[str, Any]
    ) -> List[ProtocolTransition]:
        """Get available transitions for a protocol based on context."""
        if protocol_name not in self.protocols:
            raise ValueError(f"Unknown protocol: {protocol_name}")

        protocol = self.protocols[protocol_name]
        return [t for t in protocol.transitions if t.condition(context)]

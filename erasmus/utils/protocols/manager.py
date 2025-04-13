"""Protocol manager for loading and executing protocols."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Set

from pydantic import BaseModel, Field, ConfigDict

from erasmus.utils.logging import get_logger
from erasmus.utils.paths import PathManager
from .base import Protocol, ProtocolTransition, ProtocolArtifact

logger = get_logger(__name__)


class ProtocolRegistry(BaseModel):
    """Registry containing all protocols and their transitions."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    agents: List[Protocol] = Field(default_factory=list)
    workflow_transitions: List[ProtocolTransition] = Field(default_factory=list)


class ProtocolManager(BaseModel):
    """Manages protocol loading, registration, and execution."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    protocols: Dict[str, Protocol] = Field(default_factory=dict)
    prompt_functions: Dict[str, Callable] = Field(default_factory=dict)
    event_handlers: Dict[str, List[Callable]] = Field(default_factory=dict)
    path_manager: PathManager = Field(default_factory=PathManager)
    transitions: List[ProtocolTransition] = Field(default_factory=list)

    # TODO: Add a global context field in the rules file to store shared context across protocols
    # This will allow protocols to access common information without passing it explicitly
    # Implementation should include:
    # 1. Reading global context from rules file
    # 2. Merging with protocol-specific context
    # 3. Updating rules file when global context changes

    @classmethod
    async def create(cls) -> "ProtocolManager":
        """Create a new ProtocolManager instance."""
        instance = cls()
        instance.path_manager.ensure_directories()
        await instance.load_registry()
        await instance.register_default_prompts()
        return instance

    async def load_registry(self) -> None:
        """Load the protocol registry from the registry file."""
        registry_path = self.path_manager.registry_file
        if not registry_path.exists():
            logger.info(f"Creating new registry file at: {registry_path}")
            registry_data = {"agents": [], "workflow_transitions": []}
            with open(registry_path, "w") as f:
                json.dump(registry_data, f, indent=2)
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
                    file_path=self.path_manager.get_protocol_file(agent["name"]),
                )
                self.protocols[protocol.name] = protocol
                logger.info(f"Loaded protocol: {protocol.name}")

            # Load workflow transitions
            self.transitions = [
                ProtocolTransition(**transition)
                for transition in registry_data.get("workflow_transitions", [])
            ]
            logger.info(f"Loaded {len(self.transitions)} workflow transitions")

        except Exception as e:
            logger.error(f"Error loading registry: {e}")

    def register_prompt_function(self, protocol_name: str, prompt_function: Callable) -> None:
        """Register a prompt function for a protocol."""
        if protocol_name not in self.protocols:
            logger.warning(f"Cannot register prompt function for unknown protocol: {protocol_name}")
            return

        self.prompt_functions[protocol_name] = prompt_function
        logger.info(f"Registered prompt function for protocol: {protocol_name}")

    async def register_default_prompts(self) -> None:
        """Register default prompt functions for all protocols."""
        for protocol in self.protocols.values():
            if not protocol.file_path or not protocol.file_path.exists():
                logger.warning(f"No file path for protocol: {protocol.name}")
                continue

            try:
                # Read the protocol content from the file
                with open(protocol.file_path, "r") as f:
                    protocol_content = f.read()

                # Create a prompt function that formats the protocol name and context
                async def create_prompt(protocol_name, content):
                    async def prompt(context):
                        # Ensure context is a dictionary
                        if not isinstance(context, dict):
                            context = {"context": context}

                        # Add protocol-specific context
                        context["protocol_name"] = protocol_name

                        # Return the formatted prompt
                        return f"# {protocol_name}\n\n{content}\n\n## Context\n\n{json.dumps(context, indent=2)}"

                    return prompt

                # Register the prompt function
                protocol.prompt = await create_prompt(protocol.name, protocol_content)
                logger.info(f"Registered prompt for protocol: {protocol.name}")

            except Exception as e:
                logger.error(f"Error loading markdown files: {e}")
                continue

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

    async def execute_protocol(self, name: str, context: dict) -> List[ProtocolTransition]:
        """Execute a protocol and return possible next transitions."""
        protocol = self.get_protocol(name)
        if not protocol:
            raise ValueError(f"Protocol not found: {name}")

        # Ensure context is a dictionary
        if not isinstance(context, dict):
            context = {"context": context}

        # Add protocol-specific context
        context["protocol_name"] = protocol.name
        context["protocol_role"] = protocol.role

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

    async def activate_protocol(self, protocol_name: str) -> bool:
        """Activate a protocol."""
        protocol = self.get_protocol(protocol_name)
        if not protocol:
            logger.error(f"Cannot activate unknown protocol: {protocol_name}")
            return False

        await self._emit_event("protocol_activated", {"protocol": protocol})
        return True

    async def complete_protocol(self, protocol_name: str, result: Dict[str, Any]) -> bool:
        """Complete a protocol."""
        protocol = self.get_protocol(protocol_name)
        if not protocol:
            logger.error(f"Cannot complete unknown protocol: {protocol_name}")
            return False

        await self._emit_event("protocol_completed", {"protocol": protocol, "result": result})
        return True

    def get_transitions(self, protocol_name: str) -> List[ProtocolTransition]:
        """Get all transitions for a protocol."""
        return [t for t in self.transitions if t.from_agent == protocol_name]

    def get_protocol_transitions(
        self, protocol_name: str, context: Dict[str, Any]
    ) -> List[ProtocolTransition]:
        """Get available transitions for a protocol based on context."""
        if protocol_name not in self.protocols:
            raise ValueError(f"Unknown protocol: {protocol_name}")

        # Ensure context is a dictionary
        if not isinstance(context, dict):
            context = {"context": context}

        # Add protocol-specific context
        context["protocol_name"] = protocol_name
        context["protocol_role"] = self.protocols[protocol_name].role

        return [
            t for t in self.transitions if t.from_agent == protocol_name and t.condition(context)
        ]

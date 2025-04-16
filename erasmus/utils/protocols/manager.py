"""Protocol manager for loading and executing protocols."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from erasmus.utils.logging import get_logger
from erasmus.utils.paths import PathManager

from .base import Protocol, ProtocolTransition

logger = get_logger(__name__)


class ProtocolRegistry(BaseModel):
    """Registry containing all protocols and their transitions."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    agents: List[Protocol] = Field(default_factory=list)
    workflow_transitions: List[ProtocolTransition] = Field(default_factory=list)


class ProtocolManager(BaseModel):
    """Manages protocol files and their registration."""

    path_manager: PathManager = Field(default_factory=PathManager)
    registry: Dict[str, Any] = Field(default_factory=dict)
    event_handlers: Dict[str, List[Callable]] = Field(default_factory=dict)
    prompt_functions: Dict[str, Callable] = Field(default_factory=dict)
    transitions: List[ProtocolTransition] = Field(default_factory=list)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        protocols_dir: Optional[Path] = None,
        stored_protocols_dir: Optional[Path] = None,
        registry_file: Optional[Path] = None,
        path_manager: Optional[PathManager] = None,
        **data,
    ):
        """Initialize the ProtocolManager.

        Args:
            protocols_dir: Optional path to protocols directory
            stored_protocols_dir: Optional path to stored protocols directory
            registry_file: Optional path to registry file
            path_manager: Optional PathManager instance
            **data: Additional data for BaseModel
        """
        if path_manager:
            data["path_manager"] = path_manager
        elif protocols_dir and stored_protocols_dir and registry_file:
            # Create a custom PathManager with the provided paths
            project_root = protocols_dir.parent.parent
            data["path_manager"] = PathManager(project_root=project_root)
            data["path_manager"].protocols_dir = protocols_dir
            data["path_manager"].stored_protocols_dir = stored_protocols_dir
            data["path_manager"].registry_file = registry_file
        else:
            # Create a default PathManager with current directory
            data["path_manager"] = PathManager(project_root=Path.cwd())

        super().__init__(**data)

    @classmethod
    async def create(cls) -> "ProtocolManager":
        """Create a new ProtocolManager instance."""
        instance = cls()
        try:
            instance.path_manager.ensure_directories()
            await instance.load_registry()
            await instance.register_default_prompts()
        except Exception as e:
            logger.error(f"Error creating ProtocolManager: {e}")
            # Optionally, you could re-raise the exception or handle it differently
            raise
        return instance

    async def load_registry(self) -> Dict[str, Any]:
        """Load the protocol registry from disk."""
        registry_file = self.path_manager.registry_file
        if not registry_file.exists():
            logger.info(f"Registry file not found at {registry_file}, creating new registry")
            self.registry = {}
            return self.registry
        try:
            with open(registry_file, "r") as f:
                self.registry = json.load(f)
                return self.registry
        except Exception as e:
            logger.error(f"Failed to load registry from {registry_file}: {e}")
            self.registry = {}
            return self.registry

    async def register_default_prompts(self) -> None:
        """Register default prompt functions for all protocols."""
        protocols_dir = self.path_manager.protocols_dir / "stored"
        registry_file = self.path_manager.registry_file

        # Ensure the protocols directory exists
        if not protocols_dir.exists():
            logger.warning(f"Protocols directory not found: {protocols_dir}")
            return

        # Find all markdown files in the stored protocols directory
        protocol_files = list(protocols_dir.glob("*.md"))

        if not protocol_files:
            logger.info("No protocol files found in stored protocols directory")
            return

        for protocol_file in protocol_files:
            protocol_name = protocol_file.stem

            try:
                # Read the protocol content from the file
                with open(protocol_file, "r") as f:
                    protocol_content = f.read().strip()

                # If protocol not in registry, add it
                if protocol_name not in self.registry:
                    self.registry[protocol_name] = {
                        "name": protocol_name,
                        "description": f"Default protocol for {protocol_name}",
                        "file_path": str(protocol_file),
                        "protocol_content": protocol_content,
                    }
                    logger.info(f"Added protocol {protocol_name} to registry")

            except IOError as e:
                logger.error(f"Error reading protocol file {protocol_file}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error processing protocol {protocol_name}: {e}")

        # Optionally save the updated registry
        try:
            # Ensure the directory exists
            registry_file.parent.mkdir(parents=True, exist_ok=True)

            # Write the serializable registry to the file
            with open(registry_file, "w") as f:
                serializable_registry = {}
                for name, protocol in self.registry.items():
                    # Ensure protocol is a dictionary or has model_dump method
                    if hasattr(protocol, "model_dump"):
                        protocol_dict = protocol.model_dump()
                    elif not isinstance(protocol, dict):
                        protocol_dict = {"name": name, "description": "", "file_path": ""}
                    else:
                        protocol_dict = protocol

                    # Convert PosixPath to string
                    serializable_registry[name] = {
                        "name": protocol_dict.get("name", name),
                        "description": protocol_dict.get("description", ""),
                        "file_path": str(protocol_dict.get("file_path", "")),
                        "protocol_content": protocol_dict.get("protocol_content", ""),
                    }
                json.dump(serializable_registry, f, indent=2)

            logger.info(f"Registry saved to {registry_file}")
        except Exception as e:
            logger.error(f"Failed to save updated registry: {e}")

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

            # Ensure stored protocols directory exists
            stored_protocols_dir = self.path_manager.stored_protocols_dir
            stored_protocols_dir.mkdir(parents=True, exist_ok=True)

            for agent in registry_data.get("agents", []):
                # Sanitize protocol name for file path
                safe_name = agent["name"].replace("/", "_").replace("\\", "_").strip()

                # Check for existing protocol file
                protocol_file = None

                # First check in the stored protocols directory
                stored_file = stored_protocols_dir / f"{safe_name}.md"
                if stored_file.exists():
                    protocol_file = stored_file
                    logger.info(f"Found existing protocol file: {protocol_file}")

                # If not found in stored directory, check in the default protocols directory
                if not protocol_file:
                    default_file = self.path_manager.protocols_dir / f"{safe_name}.md"
                    if default_file.exists():
                        protocol_file = default_file
                        logger.info(f"Found protocol file in default directory: {protocol_file}")

                # If still not found, create a new file in the stored directory
                if not protocol_file:
                    protocol_file = stored_file
                    # Create a basic protocol template
                    protocol_content = f"""# {agent["name"]}

## Role
{agent["role"]}

## Triggers
{", ".join(agent.get("triggers", []))}

## Produces
{", ".join(agent.get("produces", []))}

## Consumes
{", ".join(agent.get("consumes", []))}

## Description
This is a protocol for the {agent["name"]} role.
"""
                    protocol_file.write_text(protocol_content)
                    logger.info(f"Created new protocol file: {protocol_file}")

                protocol = Protocol(
                    name=agent["name"],  # Keep original name for display
                    role=agent["role"],
                    triggers=agent.get("triggers", []),
                    produces=agent.get("produces", []),
                    consumes=agent.get("consumes", []),
                    file_path=protocol_file,
                )
                self.registry[protocol.name] = protocol
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
        if protocol_name not in self.registry:
            logger.warning(f"Cannot register prompt function for unknown protocol: {protocol_name}")
            return

        self.prompt_functions[protocol_name] = prompt_function
        logger.info(f"Registered prompt function for protocol: {protocol_name}")

    def save_registry(self) -> None:
        """Save the protocol registry to a JSON file."""
        try:
            # Create a serializable version of the registry
            serializable_registry = {}
            for name, protocol in self.registry.items():
                # Convert Protocol objects to dictionaries
                if hasattr(protocol, "model_dump"):
                    serializable_registry[name] = protocol.model_dump()
                else:
                    serializable_registry[name] = {
                        "name": protocol.get("name", name),
                        "description": protocol.get("description", ""),
                        "file_path": protocol.get("file_path", ""),
                    }

            # Ensure the directory exists
            registry_file = self.path_manager.agent_registry_file
            registry_file.parent.mkdir(parents=True, exist_ok=True)

            # Write the serializable registry to the file
            with open(registry_file, "w") as f:
                json.dump(serializable_registry, f, indent=2)

            logger.info(f"Registry saved to {registry_file}")
        except Exception as e:
            logger.error(f"Failed to save registry to {registry_file}: {e}")

    def register_protocol(self, name: str, description: str, file_path: Path) -> None:
        """Register a new protocol in the registry."""
        if name in self.registry:
            logger.warning(f"Protocol {name} already exists in registry")
            return

        self.registry[name] = {
            "description": description,
            "file_path": str(file_path),
            "created_at": datetime.now().isoformat(),
        }
        self.save_registry()
        logger.info(f"Registered protocol {name}")

    def unregister_protocol(self, name: str) -> None:
        """Remove a protocol from the registry."""
        if name not in self.registry:
            logger.warning(f"Protocol {name} not found in registry")
            return

        del self.registry[name]
        self.save_registry()
        logger.info(f"Unregistered protocol {name}")

    def get_protocol(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a protocol from the registry by name."""
        return self.registry.get(name)

    def list_protocols(self) -> List[Dict[str, Any]]:
        """List all registered protocols."""
        return list(self.registry.values())

    def get_protocol_file(self, name: str) -> Optional[Path]:
        """Get the file path for a protocol by name."""
        protocol = self.get_protocol(name)
        if not protocol:
            return None
        return Path(protocol.get("file_path", ""))

    def get_protocol_json(self, name: str) -> Optional[Path]:
        """Get the JSON file path for a protocol by name."""
        protocol = self.get_protocol(name)
        if not protocol:
            return None
        file_path = Path(protocol.get("file_path", ""))
        return file_path.with_suffix(".json")

    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register an event handler for a specific event type."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def _emit_event(self, event_type: str, data: Any) -> None:
        """Emit an event to all registered handlers."""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                handler(data)

    async def execute_protocol(self, name: str, context: dict) -> List[ProtocolTransition]:
        """Execute a protocol and return possible next transitions."""
        protocol = self.get_protocol(name)
        if not protocol:
            raise ValueError(f"Protocol not found: {name}")

        # Ensure context is a dictionary
        if not isinstance(context, dict):
            context = {"context": context}

        # Add protocol-specific context
        context["protocol_name"] = protocol["name"]
        context["protocol_role"] = protocol["role"]

        # Execute the protocol
        artifacts = await protocol.execute(context)

        # Find possible next transitions based on produced artifacts
        possible_transitions = []
        for artifact in artifacts:
            transitions = [
                t
                for t in self.transitions
                if t.from_agent == protocol["name"] and t.artifact == artifact.name
            ]
            possible_transitions.extend(transitions)

        return possible_transitions

    def get_protocol(self, protocol_name: str) -> Optional[Dict[str, Any]]:
        """Get a protocol by name."""
        return self.registry.get(protocol_name)

    def list_protocols(self) -> List[Dict[str, Any]]:
        """List all available protocols."""
        return list(self.registry.values())

    def get_transitions_from(self, protocol_name: str) -> List[ProtocolTransition]:
        """Get all transitions originating from a protocol."""
        return [t for t in self.transitions if t.from_agent == protocol_name]

    def get_transitions_to(self, protocol_name: str) -> List[ProtocolTransition]:
        """Get all transitions targeting a protocol."""
        return [t for t in self.transitions if t.to_agent == protocol_name]

    async def activate_protocol(self, protocol_name: str) -> bool:
        """Activate a protocol by name."""
        try:
            # Check if the protocol exists in the registry
            if protocol_name not in self.registry:
                logger.warning(f"Protocol {protocol_name} not found in registry")
                return False

            # Perform any necessary activation steps
            # This could involve setting a default agent, initializing resources, etc.
            logger.info(f"Activating protocol: {protocol_name}")

            return True
        except Exception as e:
            logger.error(f"Error activating protocol {protocol_name}: {e}")
            return False

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
        if protocol_name not in self.registry:
            raise ValueError(f"Unknown protocol: {protocol_name}")

        # Ensure context is a dictionary
        if not isinstance(context, dict):
            context = {"context": context}

        # Add protocol-specific context
        context["protocol_name"] = protocol_name
        context["protocol_role"] = self.registry[protocol_name]["role"]

        return [
            t for t in self.transitions if t.from_agent == protocol_name and t.condition(context)
        ]

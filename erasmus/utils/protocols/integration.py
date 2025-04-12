from typing import Dict, Any, List, Optional
import os
from pathlib import Path

from erasmus.utils.logging import get_logger
from erasmus.utils.paths import SetupPaths
from erasmus.utils.context import handle_agent_context

from .server import ProtocolServer
from .base import Protocol, ProtocolArtifact, ProtocolTransition

logger = get_logger(__name__)


class ProtocolIntegration:
    """Integration of the protocol system with the Erasmus framework."""

    def __init__(self, setup_paths: SetupPaths):
        self.setup_paths = setup_paths
        self.protocol_server = ProtocolServer()
        self.registry_path = (
            self.setup_paths.project_root
            / "erasmus"
            / "utils"
            / "protocols"
            / "agent_registry.json"
        )

    async def initialize(self) -> None:
        """Initialize the protocol system."""
        if not os.path.exists(self.registry_path):
            logger.warning(f"Registry file not found: {self.registry_path}")
            return

        await self.protocol_server.initialize(str(self.registry_path))
        logger.info("Protocol system initialized")

    def register_protocol_prompts(self) -> None:
        """Register prompt functions for each protocol."""
        # This is where you would register your prompt functions for each protocol
        # Example:
        # self.protocol_server.register_prompt_function("Product Owner Agent", product_owner_prompt)
        # self.protocol_server.register_prompt_function("Developer Agent", developer_prompt)
        pass

    async def execute_protocol(self, protocol_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a protocol and return the results."""
        try:
            response = await self.protocol_server.execute_protocol(protocol_name, context)

            # Process artifacts
            for artifact in response.artifacts:
                if artifact.type == "file" and artifact.path:
                    # Handle file artifacts
                    path = Path(artifact.path)
                    if artifact.content:
                        with open(path, "w") as f:
                            f.write(artifact.content)
                        logger.info(f"Wrote file artifact: {path}")

                # Handle other artifact types as needed

            # Return the results
            return {
                "artifacts": [a.dict() for a in response.artifacts],
                "next_transitions": [t.dict() for t in response.next_transitions],
            }
        except Exception as e:
            logger.error(f"Error executing protocol {protocol_name}: {e}")
            raise

    def get_protocol(self, name: str) -> Optional[Protocol]:
        """Get a protocol by name."""
        return self.protocol_server.get_protocol(name)

    def list_protocols(self) -> List[Protocol]:
        """List all available protocols."""
        return self.protocol_server.list_protocols()

    def get_protocol_transitions(
        self, name: str, direction: str = "from"
    ) -> List[ProtocolTransition]:
        """Get transitions for a protocol."""
        return self.protocol_server.get_protocol_transitions(name, direction)

    async def run_workflow(
        self, start_protocol: str, initial_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run a workflow starting from a specific protocol."""
        current_protocol = start_protocol
        context = initial_context.copy()
        results = []

        while current_protocol:
            # Execute the current protocol
            result = await self.execute_protocol(current_protocol, context)
            results.append({"protocol": current_protocol, "result": result})

            # Update context with artifacts
            for artifact in result["artifacts"]:
                context[artifact["name"]] = artifact["content"]

            # Determine next protocol based on transitions
            next_transitions = result["next_transitions"]
            if next_transitions:
                # For simplicity, just take the first transition
                # In a real system, you might want to handle multiple transitions
                next_transition = next_transitions[0]
                current_protocol = next_transition["to_agent"]
            else:
                current_protocol = None

        return {"workflow_results": results}

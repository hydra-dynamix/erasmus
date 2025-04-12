from typing import Any, List, Optional
from pydantic import BaseModel, Field
from pathlib import Path

from erasmus.utils.logging import get_logger

logger = get_logger(__name__)


class ProtocolArtifact(BaseModel):
    """Represents an artifact that can be produced or consumed by an agent."""

    name: str = Field(description="Name of the artifact")
    type: str = Field(description="Type of the artifact (e.g., 'file', 'report', 'config')")
    path: Optional[str] = Field(None, description="Path to the artifact if it's a file")
    content: Optional[Any] = Field(None, description="Content of the artifact if not a file")


class ProtocolTransition(BaseModel):
    """Represents a workflow transition between agents."""

    from_agent: str = Field(description="Name of the source agent")
    to_agent: str = Field(description="Name of the target agent")
    trigger: str = Field(description="Event that triggers this transition")
    artifact: str = Field(description="Artifact passed during transition")


class Protocol(BaseModel):
    """Base class for all agent protocols."""

    name: str = Field(description="Name of the protocol")
    role: str = Field(description="Role/responsibility of the protocol")
    file_path: str = Field(description="Path to the protocol's markdown file")
    triggers: List[str] = Field(description="Events that trigger this protocol")
    produces: List[str] = Field(description="Artifacts this protocol produces")
    consumes: List[str] = Field(description="Artifacts this protocol consumes")
    prompt: Optional[Any] = Field(None, description="Associated prompt function")

    async def execute(self, context: dict[str, Any]) -> List[ProtocolArtifact]:
        """Execute the protocol with given context."""
        if not self.prompt:
            raise ValueError(f"Protocol {self.name} has no associated prompt")

        try:
            # Execute the prompt function with the context
            result = self.prompt(context)

            # Process the result and convert to artifacts
            artifacts = await self._process_result(result)
            return artifacts
        except Exception as e:
            logger.error(f"Error executing protocol {self.name}: {e}")
            raise

    async def _process_result(self, result: Any) -> List[ProtocolArtifact]:
        """Process the result from prompt execution into artifacts."""
        artifacts: List[ProtocolArtifact] = []

        # Handle different result types
        if isinstance(result, str):
            # Simple text result
            artifacts.append(
                ProtocolArtifact(name=f"{self.name}_output", type="text", content=result)
            )
        elif isinstance(result, dict):
            # Dictionary result - convert to artifacts
            for key, value in result.items():
                if isinstance(value, str):
                    artifacts.append(ProtocolArtifact(name=key, type="text", content=value))
                elif isinstance(value, dict):
                    # Handle nested dictionaries
                    artifacts.append(ProtocolArtifact(name=key, type="json", content=value))
        elif isinstance(result, list):
            # List result - process each item
            for i, item in enumerate(result):
                if isinstance(item, str):
                    artifacts.append(
                        ProtocolArtifact(name=f"{self.name}_output_{i}", type="text", content=item)
                    )
                elif isinstance(item, dict):
                    # Handle dictionaries in the list
                    artifacts.append(
                        ProtocolArtifact(name=f"{self.name}_output_{i}", type="json", content=item)
                    )

        return artifacts

from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field, ConfigDict
from pathlib import Path
import asyncio
import json

from erasmus.utils.logging import get_logger

logger = get_logger(__name__)


class ProtocolArtifact(BaseModel):
    """Represents an artifact produced by a protocol."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    content: Any
    path: Optional[str] = None


class ProtocolTransition(BaseModel):
    """Represents a transition between protocols."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    from_agent: str
    to_agent: str
    trigger: str
    artifact: str
    condition: Callable[[Dict[str, Any]], bool] = Field(default=lambda _: True)


class Protocol(BaseModel):
    """Base class for all protocols."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    role: str
    triggers: List[str] = Field(default_factory=list)
    produces: List[str] = Field(default_factory=list)
    consumes: List[str] = Field(default_factory=list)
    markdown: str = ""
    artifacts: List[ProtocolArtifact] = Field(default_factory=list)
    transitions: List[ProtocolTransition] = Field(default_factory=list)
    prompt: Optional[Callable[[Dict[str, Any]], Any]] = None
    file_path: Optional[Path] = None

    async def execute(self, context: Dict[str, Any]) -> List[ProtocolArtifact]:
        """Execute the protocol with the given context."""
        if not self.prompt:
            raise ValueError(f"No prompt function registered for protocol: {self.name}")

        # Ensure context is a dictionary
        if not isinstance(context, dict):
            context = {"context": context}

        # Add protocol-specific context
        context["protocol_name"] = self.name
        context["protocol_role"] = self.role

        # Execute the prompt function
        prompt_result = await self.prompt(context)

        # Process artifacts
        artifacts = []

        # If prompt_result is a string, treat it as markdown content
        if isinstance(prompt_result, str):
            # Create a markdown artifact
            artifacts.append(
                ProtocolArtifact(
                    name=f"{self.name.lower().replace(' ', '_')}.md",
                    content=prompt_result,
                    path=f"erasmus/utils/protocols/stored/{self.name.lower().replace(' ', '_')}.md",
                )
            )
        # If prompt_result is a dictionary, create artifacts for each key
        elif isinstance(prompt_result, dict):
            for key, value in prompt_result.items():
                artifacts.append(
                    ProtocolArtifact(
                        name=key, content=value, path=f"erasmus/utils/protocols/stored/{key}"
                    )
                )
        # If prompt_result is a list, create artifacts for each item
        elif isinstance(prompt_result, list):
            for i, item in enumerate(prompt_result):
                artifacts.append(
                    ProtocolArtifact(
                        name=f"{self.name.lower().replace(' ', '_')}_{i}",
                        content=item,
                        path=f"erasmus/utils/protocols/stored/{self.name.lower().replace(' ', '_')}_{i}",
                    )
                )
        # If prompt_result is None or something else, create a default artifact
        else:
            artifacts.append(
                ProtocolArtifact(
                    name=f"{self.name.lower().replace(' ', '_')}",
                    content=str(prompt_result),
                    path=f"erasmus/utils/protocols/stored/{self.name.lower().replace(' ', '_')}",
                )
            )

        # Add any predefined artifacts from the protocol
        for artifact in self.artifacts:
            if artifact.name in context:
                artifacts.append(
                    ProtocolArtifact(
                        name=artifact.name, content=context[artifact.name], path=artifact.path
                    )
                )

        return artifacts

    def get_transitions(self, context: Dict[str, Any]) -> List[ProtocolTransition]:
        """Get available transitions based on context."""
        # Ensure context is a dictionary
        if not isinstance(context, dict):
            context = {"context": context}

        # Add protocol-specific context
        context["protocol_name"] = self.name
        context["protocol_role"] = self.role

        return [t for t in self.transitions if t.condition(context)]

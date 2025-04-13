from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field
from pathlib import Path
import asyncio

from erasmus.utils.logging import get_logger

logger = get_logger(__name__)


class ProtocolArtifact(BaseModel):
    """Represents an artifact produced by a protocol."""

    name: str
    content: Any
    path: Optional[str] = None


class ProtocolTransition(BaseModel):
    """Represents a transition between protocols."""

    from_agent: str
    to_agent: str
    trigger: str
    condition: Callable[[Dict[str, Any]], bool] = Field(default=lambda _: True)


class Protocol(BaseModel):
    """Base class for all protocols."""

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

        # Execute the prompt function
        prompt_result = (
            await self.prompt(context)
            if asyncio.iscoroutinefunction(self.prompt)
            else self.prompt(context)
        )

        # Process artifacts
        artifacts = []
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
        return [t for t in this.transitions if t.condition(context)]

from pydantic import BaseModel
from erasmus.utils.paths import SetupPaths
from erasmus.utils.context import (
    get_logger,
    handle_agent_context,
    PROJECT_MARKER,
    PWD,
)

logger = get_logger(__name__)


class Protocol(BaseModel):
    name: str
    description: str
    persona: str

PROTOCOL_PROJECT_OWNER = Protocol(
    name="project_owner",
    description="Project owner agent responsible for overseeing the core tracking documentation",
    protocol="""

""")

PROTOCOL_DEVELOPER = Protocol(
    name="developer",
    description="Developer agent responsible for generating code",
    protocol="""
""")

class ProtocolManager(BaseModel):
    current_protocol: Protocol
    protocols: dict[str, Protocol]

    def __init__(self, protocols: dict[str, Protocol]):
        self.protocols = protocols
        


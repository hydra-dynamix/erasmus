"""Context class for protocol state management."""

from typing import Dict, Any, Optional


class Context:
    """Context class for managing protocol state."""

    def __init__(self):
        self.active_protocol: Optional[str] = None
        self.protocol_state: Dict[str, Any] = {}
        self.protocol_artifacts: Dict[str, Any] = {}

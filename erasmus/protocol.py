"""
Protocol management functionality for Erasmus.
"""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from loguru import logger
from erasmus.utils.paths import get_path_manager
from erasmus.utils.sanatizer import _sanitize_string, _sanitize_xml_content

path_manager = get_path_manager()


class ProtocolError(Exception):
    """Exception raised for protocol-related errors."""

    pass


class ProtocolModel(BaseModel):
    """
    Represents a protocol, including its name, path, and content.
    """

    name: str
    path: str
    content: str


class ProtocolManager:
    """
    Manages protocol files for Erasmus.
    Loads base protocol templates from erasmus.erasmus/templates/protocols and custom user protocols from erasmus.erasmus/protocol.
    Provides methods to list, get, create, update, and delete protocols.
    """

    def __init__(self, base_dir: Optional[str] = None, user_dir: Optional[str] = None) -> None:
        # Always use path_manager.template_dir / 'protocols' unless base_dir is explicitly provided
        self.base_template_dir: Path = (
            Path(base_dir) if base_dir is not None else path_manager.template_dir / "protocols"
        )
        self.user_protocol_dir: Path = Path(user_dir) if user_dir else path_manager.protocol_dir
        self.base_template_dir.mkdir(parents=True, exist_ok=True)
        self.user_protocol_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Initialized ProtocolManager with base template dir: {self.base_template_dir} and user protocol dir: {self.user_protocol_dir}"
        )

    def _sanitize_name(self, protocol_name: str) -> str:
        """Sanitize a protocol name for filesystem use."""
        return _sanitize_string(protocol_name)

    def _get_protocol_path(self, protocol_name: str, is_template: bool = False) -> Path:
        """
        Get the path for a protocol file.
        Args:
            protocol_name: The protocol name
            is_template: If True, look in the template directory; else, user directory
        Returns:
            Path to the protocol file
        """
        sanitized_name = self._sanitize_name(protocol_name)
        directory = self.base_template_dir if is_template else self.user_protocol_dir
        return directory / f"{sanitized_name}.xml"

    def list_protocols(
        self, include_templates: bool = True, include_user: bool = True
    ) -> list[str]:
        """
        List all available protocol names.
        Args:
            include_templates: Include base templates
            include_user: Include user protocols
        Returns:
            List of protocol names
        """
        protocol_names = set()
        if include_templates:
            protocol_names.update(
                [protocol_path.stem for protocol_path in self.base_template_dir.glob("*.xml")]
            )
        if include_user:
            protocol_names.update(
                [protocol_path.stem for protocol_path in self.user_protocol_dir.glob("*.xml")]
            )
        return sorted(protocol_names)

    def get_protocol(self, protocol_name: str) -> Optional[ProtocolModel]:
        """
        Get a protocol by name, searching user protocols first, then templates.
        Args:
            protocol_name: The protocol name
        Returns:
            ProtocolModel if found, else None
        """
        sanitized_name = self._sanitize_name(protocol_name)
        user_path = self._get_protocol_path(sanitized_name, is_template=False)
        template_path = self._get_protocol_path(sanitized_name, is_template=True)
        if user_path.exists():
            content = user_path.read_text()
            return ProtocolModel(name=sanitized_name, path=str(user_path), content=content)
        elif template_path.exists():
            content = template_path.read_text()
            return ProtocolModel(name=sanitized_name, path=str(template_path), content=content)
        else:
            return None

    def create_protocol(self, protocol_name: str, content: str) -> ProtocolModel:
        """
        Create a new user protocol.
        Args:
            protocol_name: The protocol name
            content: The protocol content
        Returns:
            The created ProtocolModel
        Raises:
            FileExistsError: If a user protocol with the same name already exists
        """
        sanitized_name = self._sanitize_name(protocol_name)
        protocol_path = self._get_protocol_path(sanitized_name, is_template=False)
        if protocol_path.exists():
            raise FileExistsError(f"Protocol '{sanitized_name}' already exists.")
        # Use template if content is not provided or empty
        if not isinstance(content, str) or not content.strip():
            template_path = path_manager.template_dir / "protocol.xml"
            if template_path.exists():
                content = template_path.read_text()
            else:
                content = '<?xml version="1.0" encoding="UTF-8"?>\n<Protocol></Protocol>'
        else:
            # If content is not valid XML, wrap it in <Protocol>...</Protocol>
            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(content)
            except Exception:
                content = f'<?xml version="1.0" encoding="UTF-8"?>\n<Protocol>{content}</Protocol>'
        protocol_path.write_text(_sanitize_xml_content(content))
        logger.info(f"Created protocol: {sanitized_name}")
        return ProtocolModel(name=sanitized_name, path=str(protocol_path), content=content)

    def update_protocol(self, protocol_name: str, content: str) -> ProtocolModel:
        """
        Update an existing user protocol.
        Args:
            protocol_name: The protocol name
            content: The new protocol content
        Returns:
            The updated ProtocolModel
        Raises:
            FileNotFoundError: If the protocol does not exist in user protocols
        """
        sanitized_name = self._sanitize_name(protocol_name)
        protocol_path = self._get_protocol_path(sanitized_name, is_template=False)
        if not protocol_path.exists():
            raise FileNotFoundError(f"Protocol '{sanitized_name}' not found in user protocols.")
        # Ensure content is a valid XML string
        if not isinstance(content, str) or not content.strip():
            content = '<?xml version="1.0" encoding="UTF-8"?>\n<Protocol></Protocol>'
        else:
            import xml.etree.ElementTree as ET

            try:
                ET.fromstring(content)
            except Exception:
                content = f'<?xml version="1.0" encoding="UTF-8"?>\n<Protocol>{content}</Protocol>'
        protocol_path.write_text(_sanitize_xml_content(content))
        logger.info(f"Updated protocol: {sanitized_name}")
        return ProtocolModel(name=sanitized_name, path=str(protocol_path), content=content)

    def delete_protocol(self, protocol_name: str) -> None:
        """
        Delete a user protocol.
        Args:
            protocol_name: The protocol name
        Raises:
            FileNotFoundError: If the protocol does not exist in user protocols
            PermissionError: If attempting to delete a template protocol
        """
        sanitized_name = self._sanitize_name(protocol_name)
        protocol_path = self._get_protocol_path(sanitized_name, is_template=False)
        template_path = self._get_protocol_path(sanitized_name, is_template=True)
        # Prevent deletion if protocol is a template
        if template_path.exists():
            raise PermissionError(
                f"Cannot delete template protocol: '{sanitized_name}'. Only custom (user) protocols can be deleted."
            )
        if not protocol_path.exists():
            raise FileNotFoundError(f"Protocol '{sanitized_name}' not found in user protocols.")
        protocol_path.unlink()
        logger.info(f"Deleted protocol: {sanitized_name}")

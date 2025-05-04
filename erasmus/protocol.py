"""
Protocol management functionality for Erasmus.
"""

from pathlib import Path
from typing import Optional, List, Union
import typer
from pydantic import BaseModel, Field
from loguru import logger

from erasmus.utils.paths import get_path_manager
from erasmus.utils.sanatizer import _sanitize_string
from erasmus.utils.rich_console import get_console, print_panel, print_table

console = get_console()

class ProtocolError(Exception):
    """Base exception for protocol-related errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
        # Use rich console to display the error
        get_console().print(
            f"[bold red]Protocol Error:[/bold red] {message}", 
            style="bold yellow"
        )


class ProtocolNotFoundError(ProtocolError):
    """Raised when a protocol is not found."""
    pass


class ProtocolExistsError(ProtocolError):
    """Raised when attempting to create a protocol that already exists."""
    pass

path_manager = get_path_manager()


class ProtocolError(Exception):
    """Exception raised for protocol-related errors."""

    pass


class ProtocolModel(BaseModel):
    """
    Represents a protocol, including its name, path, and content.
    """
    name: str | None = Field(..., description="Sanitized protocol name")
    path: str | Path | None = Field(..., description="Absolute path to the protocol file")
    content: str | None = Field(..., description="Protocol content")

    def __str__(self) -> str:
        return f"Protocol: {self.name} (Path: {self.path})"

    def __repr__(self) -> str:
        return f"ProtocolModel(name='{self.name}', path='{self.path}')"

    def display(self) -> None:
        """Display protocol details using rich console."""
        print_panel(
            content=self.content,
            style="bold blue",
            title="Protocol",
        )


class ProtocolManager:
    """
    Manages protocol files for Erasmus.
    Loads base protocol templates from erasmus.erasmus/templates/protocols and custom user protocols from erasmus.erasmus/protocol.
    Provides methods to list, get, create, update, and delete protocols.
    """

    def __init__(self, base_dir: str | None = None, user_dir: str | None = None) -> None:
        """Initialize ProtocolManager with protocol directories."""
        try:
            self.user_protocol_dir: Path = path_manager.erasmus_dir / "protocol"
            self.template_protocol_dir: Path = path_manager.template_dir / "protocols"
            for directory in [self.user_protocol_dir, self.template_protocol_dir]:
                directory.mkdir(parents=True, exist_ok=True)
            self.protocol: ProtocolModel | None = None
            self.protocol_name: str | None = None
            self.protocol_path: Path | None = None
            logger.info(
                f"Initialized ProtocolManager: User Protocols at {self.user_protocol_dir}, "
                f"Template Protocols at {self.template_protocol_dir}"
            )
        except Exception as e:
            get_console().print_exception()
            raise ProtocolError(f"Failed to initialize ProtocolManager: {e}")

    def _templates(self) -> List[str | None]:
        try:
            return [template.name for template in self.template_protocol_dir.iterdir()]
        except Exception as e:
            get_console().print_exception()
            raise ProtocolError(f"Failed to retrieve template protocols: {e}")

    def _user_protocols(self) -> List[str | None]:
        try:
            return [protocol.name for protocol in self.user_protocol_dir.iterdir()]
        except Exception as e:
            get_console().print_exception()
            raise ProtocolError(f"Failed to retrieve user protocols: {e}")

    def _sanitize_name(self, protocol_name: str) -> str:
        """Sanitize a protocol name for filesystem use."""
        # Remove .md extension before sanitization
        name_without_ext = protocol_name.removesuffix('.md')
        return _sanitize_string(name_without_ext)

    def _get_protocol_path(self, protocol_name: str) -> Path:
        """Get the path for a protocol file.

        Args:
            protocol_name: Name of the protocol

        Returns:
            Path to the protocol file

        Raises:
            FileNotFoundError: If the protocol file does not exist
        """
        try:
            # Check user protocols first
            user_path = self.user_protocol_dir / f"{protocol_name.removesuffix('.md')}.md"
            template_path = self.template_protocol_dir / f"{protocol_name.removesuffix('.md')}.md"

            if user_path.exists():
                return user_path
            if template_path.exists():
                return template_path

            raise FileNotFoundError(f"Protocol '{protocol_name}' not found")
        except Exception as e:
            get_console().print_exception()
            raise ProtocolError(f"Failed to resolve protocol path: {e}")

    def _write_protocol(self, protocol_name: str, content: str) -> ProtocolModel:
        """Write a protocol file with robust error handling.

        Args:
            protocol_name: Name of the protocol
            content: Content of the protocol

        Returns:
            ProtocolModel of the created/updated protocol

        Raises:
            ProtocolError: If protocol writing fails
        """
        try:
            sanitized_name = self._sanitize_name(protocol_name)
            
            # Determine protocol path (user directory)
            if not sanitized_name.endswith('.md'):
                sanitized_name += '.md'
            protocol_path = self.user_protocol_dir / sanitized_name
            
            # Handle existing protocol
            if protocol_path.exists():
                print_panel(
                    content="[yellow]Protocol already exists[/yellow]", 
                    title="Overwrite Confirmation", 
                    style="bold yellow"
                )
                confirm = typer.confirm("Overwrite existing protocol?", default=False)
                if not confirm:
                    raise FileExistsError(f"Protocol '{sanitized_name}' already exists")
            
            # Use template if content is empty
            if not content.strip():
                template_path = path_manager.template_dir / "protocol.md"
                content = template_path.read_text() if template_path.exists() else sanitized_name
            
            # Write protocol
            protocol_path.write_text(content)
            
            # Create protocol model
            protocol = ProtocolModel(
                name=sanitized_name, 
                path=str(protocol_path), 
                content=content
            )
            
            # Log and display
            logger.info(f"Created/Updated protocol: {sanitized_name}")
            protocol.display()
            
            self.protocol = protocol
            return protocol
        except Exception as e:
            get_console().print_exception()
            raise ProtocolError(f"Failed to write protocol {protocol_name}: {e}")

    def _read_protocol(self, protocol_name: str) -> str:
        sanitized_name = self._sanitize_name(protocol_name)
        protocol_path = self._get_protocol_path(sanitized_name)
        if not protocol_path.exists():
            raise FileNotFoundError(f"Protocol '{sanitized_name}' not found")
        return protocol_path.read_text()

    def _load_protocol(self, protocol_name: str) -> ProtocolModel:
        content = self._read_protocol(protocol_name)
        self.protocol = ProtocolModel(name=protocol_name, path=str(self._get_protocol_path(protocol_name)), content=content)
        return self.protocol

    def _update_context(self):
        # Ensure a protocol is set
        if not hasattr(self, 'protocol') or self.protocol is None:
            print("[CRITICAL] No protocol set. Skipping context update.")
            logger.warning("No protocol set. Skipping context update.")
            return
        
        try:
            # Read context files
            architecture = path_manager.architecture_file.read_text()
            progress = path_manager.progress_file.read_text()
            tasks = path_manager.tasks_file.read_text()
            
            # Prepare rules file path
            rules_path = path_manager.rules_file
            context_template_path = path_manager.template_dir / "meta_rules.md"
            
            # Log detailed debug information
            print(f"[DEBUG] Updating rules file: {rules_path}")
            print(f"[DEBUG] Using template: {context_template_path}")
            print(f"[DEBUG] Protocol: {self.protocol.name}")
            print(f"[DEBUG] Protocol content length: {len(self.protocol.content)}")
            
            # Read template and replace placeholders
            template_content = context_template_path.read_text()
            
            # Print out placeholders before replacement
            print("[DEBUG] Before replacement:")
            print(f"Architecture placeholder: {template_content.count('<!-- Architecture content -->')}")
            print(f"Progress placeholder: {template_content.count('<!-- Progress content -->')}")
            print(f"Tasks placeholder: {template_content.count('<!-- Tasks content -->')}")
            print(f"Protocol placeholder: {template_content.count('<!-- Protocol content -->')}")
            
            template_content = template_content.replace("<!-- Architecture content -->", architecture)
            template_content = template_content.replace("<!-- Progress content -->", progress)
            template_content = template_content.replace("<!-- Tasks content -->", tasks)
            template_content = template_content.replace("<!-- Protocol content -->", self.protocol.content)
            
            # Print out content before writing
            print("[DEBUG] Template content preview:")
            print(template_content[:500] + "...")
            
            # Write updated content to rules file
            rules_path.write_text(template_content)
            
            print(f"[SUCCESS] Successfully updated rules file with protocol: {self.protocol.name}")
            logger.info(f"Successfully updated rules file with protocol: {self.protocol.name}")
        except Exception as e:
            print(f"[ERROR] Failed to update context: {e}")
            logger.error(f"Failed to update context: {e}")
            get_console().print_exception()

    def list_protocols(self, templates: bool = True, user: bool = True) -> List[str]:
        """List available protocols.

        Args:
            templates: Include template protocols
            user: Include user protocols

        Returns:
            List of protocol names

        Raises:
            ProtocolError: If listing protocols fails
        """
        try:
            protocol_names = []
            if templates:
                protocol_names.extend(self._templates())
            if user:
                protocol_names.extend(self._user_protocols())
        
            # Use rich console to display protocols
            protocol_names = [protocol for protocol in protocol_names if protocol.endswith('.md')]
            if protocol_names:
                # Prepare rows for print_table
                protocol_rows = [
                    [name, "Template" if name in self._templates() else "User"]
                    for name in sorted(protocol_names)
                ]
                
                # Use print_table from rich_console
                print_table(
                    ["Protocol Name", "Type"], 
                    protocol_rows, 
                    title="Available Protocols"
                )
            else:
                print_panel(
                    content="[yellow]No protocols found.[/yellow]", 
                    title="Protocols"
                )
        
            return sorted(protocol_names)
        except Exception as e:
            get_console().print_exception()
            raise ProtocolError(f"Failed to list protocols: {e}")

    def load_protocol(self, protocol_name: Optional[str] = None) -> Optional[ProtocolModel]:
        """Load a protocol by name.

        Args:
            protocol_name: Optional name of the protocol to load. If None, 
                          will prompt for interactive selection.

        Returns:
            Loaded ProtocolModel or None

        Raises:
            ProtocolNotFoundError: If the protocol cannot be found
        """
        try:
            # If no protocol name provided, select interactively
            if protocol_name is None:
                return self.select_protocol_interactively()
            
            # Sanitize the protocol name
            sanitized_name = self._sanitize_name(protocol_name)
            
            # Search for protocol in user and template directories
            protocol_file = None
            user_protocol_path = self.user_protocol_dir / f"{sanitized_name}.md"
            template_protocol_path = self.template_protocol_dir / f"{sanitized_name}.md"
            
            if user_protocol_path.exists():
                protocol_file = user_protocol_path
            elif template_protocol_path.exists():
                protocol_file = template_protocol_path
            else:
                raise ProtocolNotFoundError(f"Protocol '{sanitized_name}' not found")
            
            # Read protocol content
            protocol_content = protocol_file.read_text()
            
            # Create protocol model
            protocol = ProtocolModel(
                name=sanitized_name,
                path=protocol_file,
                content=protocol_content
            )
            
            # Display protocol details
            protocol.display()
            
            # Set current protocol
            logger.debug(f"Setting protocol: {protocol.name}")
            logger.debug(f"Protocol content length: {len(protocol.content)}")
            logger.debug(f"Protocol path: {protocol.path}")
            
            self.protocol = protocol
            
            # Verify protocol is set
            if not hasattr(self, 'protocol') or self.protocol is None:
                logger.error("Protocol not set correctly!")
                raise ValueError("Failed to set protocol")
            
            # Update context with the loaded protocol
            try:
                # Removed direct call to _update_context()
                logger.info(f"Protocol {sanitized_name} loaded successfully")
            except Exception as update_error:
                logger.error(f"Failed to update context: {update_error}")
                get_console().print_exception()
            
            return protocol
        
        except FileNotFoundError:
            raise ProtocolNotFoundError(f"Protocol '{protocol_name}' not found")
        except Exception as e:
            get_console().print_exception()
            raise ProtocolError(f"Failed to load protocol {protocol_name}: {e}")
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
        self._write_protocol(protocol_name, content)
        return self.protocol
        
    def delete_protocol(self, protocol_name: str) -> None:
        """Delete a user protocol.

        Args:
            protocol_name: The protocol name
        Raises:
            FileNotFoundError: If the protocol does not exist in user protocols
            PermissionError: If attempting to delete a template protocol
        """
        sanitized_name = self._sanitize_name(protocol_name)
        
        # Check if the protocol is a template
        template_path = self.template_protocol_dir / f"{sanitized_name}.md"
        user_path = self.user_protocol_dir / f"{sanitized_name}.md"
        
        if template_path.exists():
            raise PermissionError(f"Cannot delete template protocol: {sanitized_name}")
        
        if not user_path.exists():
            raise FileNotFoundError(f"Protocol '{sanitized_name}' not found in user protocols.")
        
        user_path.unlink()
        logger.info(f"Deleted protocol: {sanitized_name}")

    def update_protocol(self, protocol_name: str, content: str) -> None:
        """
        Update an existing user protocol.
        Args:
            protocol_name: The protocol name
            content: The new protocol content
        Raises:
            FileNotFoundError: If the protocol does not exist in user protocols
        """
        self._write_protocol(protocol_name, content)
        return self.protocol

    def select_protocol_interactively(self, prompt_title: str, error_title: str) -> str:
        """
        Interactively select and load a protocol, merging it into the rules file with current context.
        Args:
            prompt_title: Title for the interactive selection prompt
            error_title: Title for error messages
        Returns:
            The selected protocol name
        Raises:
            ProtocolError: If no protocols are found or selection fails
        """
        protocols = self.list_protocols()
        if not protocols:
            raise ProtocolError("No protocols found.")
        protocol_rows = [
            [str(index + 1), protocol_name] for index, protocol_name in enumerate(protocols)
        ]
        print_table(["#", "Protocol Name"], protocol_rows, title=prompt_title)
        choice = typer.prompt("Select a protocol by number or name")
        selected = None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(protocols):
                selected = protocols[index - 1]
        else:
            if choice in protocols:
                selected = choice
        if not selected:
            print_table(
                ["Error"],
                [[f"Invalid selection: {choice}"]],
                title=error_title,
            )
            return self.select_protocol_interactively(prompt_title, error_title)
        self.load_protocol(selected)
        return selected
        
def get_protocol_manager() -> ProtocolManager:
    return ProtocolManager()
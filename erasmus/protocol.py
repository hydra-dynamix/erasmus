"""
Protocol management functionality for Erasmus.
"""

from pathlib import Path
from typing import Union # Keep Union for now if used with more than two types, otherwise remove if not needed.
import typer
from pydantic import BaseModel, Field

from erasmus.utils.paths import get_path_manager
from erasmus.utils.sanatizer import _sanitize_string
from erasmus.utils.rich_console import get_console, print_panel, print_table, get_console_logger

console = get_console()
logger = get_console_logger()

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
            self._load_current_protocol_from_file() # Attempt to load current protocol
        except Exception as error:
            get_console().print_exception()
            raise ProtocolError(f"Failed to initialize ProtocolManager: {error}")

    def _load_current_protocol_from_file(self) -> None:
        """
        Attempts to load the protocol specified in .erasmus/current_protocol.txt.
        If found and valid, sets self.protocol.
        """
        current_protocol_file = path_manager.erasmus_dir / "current_protocol.txt"
        if current_protocol_file.exists() and current_protocol_file.is_file():
            protocol_name_from_file = ""  # Initialize to prevent unbound error in except
            try:
                protocol_name_from_file = current_protocol_file.read_text().strip()
                if protocol_name_from_file:
                    logger.info(f"Found current protocol name in file: '{protocol_name_from_file}'")

                    clean_name_for_model = self._sanitize_name(protocol_name_from_file).removesuffix('.md')
                    resolved_protocol_path = self._get_protocol_path(protocol_name_from_file)
                    content = resolved_protocol_path.read_text()

                    self.protocol = ProtocolModel(
                        name=clean_name_for_model,
                        path=str(resolved_protocol_path),
                        content=content
                    )
                    logger.info(f"Successfully loaded and set active protocol to '{self.protocol.name}' from current_protocol.txt")
                else:
                    logger.warning("current_protocol.txt is empty. No protocol pre-loaded.")
            except FileNotFoundError:
                logger.warning(f"Protocol '{protocol_name_from_file}' (from current_protocol.txt) not found at expected path.")
            except Exception as error:
                logger.error(f"Error loading protocol '{protocol_name_from_file}' from current_protocol.txt: {error}")
                self.protocol = None  # Ensure protocol is None if loading fails
        else:
            logger.debug("current_protocol.txt not found or is not a file. No protocol pre-loaded.")

    def _templates(self) -> list[str | None]:
        try:
            return [template.name for template in self.template_protocol_dir.iterdir()]
        except Exception as error:
            get_console().print_exception()
            raise ProtocolError(f"Failed to retrieve template protocols: {error}")

    def _user_protocols(self) -> list[str | None]:
        try:
            return [protocol.name for protocol in self.user_protocol_dir.iterdir()]
        except Exception as error:
            get_console().print_exception()
            raise ProtocolError(f"Failed to retrieve user protocols: {error}")

    def _sanitize_name(self, protocol_name: str | ProtocolModel) -> str:
        """Sanitize a protocol name for filesystem use.
        
        Args:
            protocol_name: Either a string or a ProtocolModel instance
        
        Returns:
            Sanitized protocol name without .md extension
        """
        # If we got a ProtocolModel, get its name
        if isinstance(protocol_name, ProtocolModel):
            name_str = protocol_name.name
        else:
            name_str = str(protocol_name)
        
        # Remove .md extension before sanitization
        name_without_ext = name_str.removesuffix('.md')
        return _sanitize_string(name_without_ext)

    def _get_protocol_path(self, protocol_name: str | ProtocolModel) -> Path:
        """Get the path to a protocol file, checking user protocols first, then templates.

        Args:
            protocol_name: Name of the protocol to find (string or ProtocolModel)

        Returns:
            Path to the protocol file

        Raises:
            FileNotFoundError: If protocol file not found in user or template directories
        """
        try:
            # If we got a ProtocolModel, get its name
            if isinstance(protocol_name, ProtocolModel):
                name_str = protocol_name.name
            else:
                name_str = str(protocol_name)
            
            # Ensure .md extension
            if not name_str.endswith('.md'):
                name_str = f"{name_str}.md"

            # Check user protocols first
            user_path = self.user_protocol_dir / name_str
            template_path = self.template_protocol_dir / name_str

            if user_path.exists():
                return user_path
            elif template_path.exists():
                return template_path
            else:
                raise FileNotFoundError(f"Protocol '{name_str}' not found in user or template directories")
        except Exception as error:
            get_console().print_exception()
            raise ProtocolError(f"Failed to get protocol path: {error}")

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
        except Exception as error:
            get_console().print_exception()
            raise ProtocolError(f"Failed to write protocol {protocol_name}: {error}")

    def _read_protocol(self, protocol_name: str) -> str:
        sanitized_name = self._sanitize_name(protocol_name)
        protocol_path = self._get_protocol_path(sanitized_name)
        if not protocol_path.exists():
            raise FileNotFoundError(f"Protocol '{sanitized_name}' not found")
        return protocol_path.read_text()

    def _load_protocol(self, protocol_name: str | ProtocolModel) -> ProtocolModel:
        # If we got a ProtocolModel, get its name
        if isinstance(protocol_name, ProtocolModel):
            name_str = protocol_name.name
        else:
            name_str = str(protocol_name)
            
        content = self._read_protocol(name_str)
        protocol_path = self._get_protocol_path(name_str)
        self.protocol = ProtocolModel(name=name_str, path=str(protocol_path), content=content)
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
        except Exception as error:
            print(f"[ERROR] Failed to update context: {error}")
            logger.error(f"Failed to update context: {error}")
            get_console().print_exception()

    def list_protocols(self, templates: bool = True, user: bool = True) -> list[dict[str, str]]:
        """List available protocols with their names and types.

        Args:
            templates: Include template protocols
            user: Include user protocols

        Returns:
            List of dictionaries, each with 'name' and 'type' keys.
            Example: [{'name': 'developer.md', 'type': 'User'}, {'name': 'ci_cd.md', 'type': 'Template'}]

        Raises:
            ProtocolError: If listing protocols fails
        """
        try:
            protocol_details = []
            template_names = self._templates() if templates else []
            user_protocol_names = self._user_protocols() if user else []

            all_names = set(template_names + user_protocol_names)
            
            for name in sorted(all_names):
                if not name.endswith('.md'):
                    continue # Skip non-markdown files if any slipped through

                is_user = name in user_protocol_names
                is_template = name in template_names

                if is_user: # User protocols take precedence if name conflict (though should be rare with .md)
                    protocol_details.append({'name': name, 'type': 'User'})
                elif is_template:
                    protocol_details.append({'name': name, 'type': 'Template'})
            
            return protocol_details
        except Exception as error:
            get_console().print_exception()
            raise ProtocolError(f"Failed to list protocols: {error}")

    def select_protocol_interactively(self, prompt_title: str = "Select Protocol", error_title: str = "Invalid Selection") -> ProtocolModel | None:
        """Interactively select a protocol from a list.

        Args:
            prompt_title: Title for the selection prompt
            error_title: Title for error messages

        Returns:
            Selected ProtocolModel or None if selection is cancelled or fails
        """
        try:
            protocols_with_details = self.list_protocols() # Now gets list of dicts
            if not protocols_with_details:
                print_panel("[yellow]No protocols available to select.[/yellow]", title="Protocols")
                return None

            # Prepare rows for print_table: ["#", "Protocol Name"]
            protocol_rows = [
                [str(idx + 1), detail['name']] 
                for idx, detail in enumerate(protocols_with_details)
            ]
            
            print_table(["#", "Protocol Name"], protocol_rows, title=prompt_title)

            while True:
                choice_str = typer.prompt("Select a protocol by number or name")
                if not choice_str:  # Handle empty input
                    print_panel(f"[yellow]Selection cannot be empty. Please enter a number or name.[/yellow]", title=error_title)
                    continue

                selected_protocol_name: str | None = None
                if choice_str.isdigit():
                    choice_idx = int(choice_str) - 1
                    if 0 <= choice_idx < len(protocols_with_details):
                        selected_protocol_name = protocols_with_details[choice_idx]['name']
                    else:
                        print_panel(f"[yellow]Invalid number: {choice_str}. Please select from the list.[/yellow]", title=error_title)
                        continue
                else: # User entered a name
                    # Find if the entered name (with or without .md) matches any protocol name
                    normalized_choice = choice_str.removesuffix('.md')
                    found_protocols = [
                        detail['name'] for detail in protocols_with_details 
                        if detail['name'].removesuffix('.md') == normalized_choice
                    ]
                    if len(found_protocols) == 1:
                        selected_protocol_name = found_protocols[0]
                    elif len(found_protocols) > 1: # Should not happen if names are unique
                        print_panel(f"[yellow]Ambiguous name: '{choice_str}'. Multiple matches found. Please be more specific or use number.[/yellow]", title=error_title)
                        continue
                    else:
                        print_panel(f"[yellow]Invalid name: '{choice_str}'. Not found in the list.[/yellow]", title=error_title)
                        continue
                
                if selected_protocol_name:
                    try:
                        # Load the selected protocol and set it as active
                        protocol_model = self._load_protocol(selected_protocol_name)
                        
                        if protocol_model: # _load_protocol returns the model on success, or None on failure
                            logger.success(f"Protocol '{protocol_model.name}' selected and loaded.")
                            # Set as current protocol
                            self.protocol = protocol_model
                            self.protocol_name = protocol_model.name
                            # Write to current_protocol.txt
                            current_protocol_file = path_manager.erasmus_dir / "current_protocol.txt"
                            current_protocol_file.write_text(selected_protocol_name)
                            return protocol_model # Return the successfully loaded model
                        else:
                            # This implies _load_and_set_active_protocol failed to load it (e.g., file not found after listing)
                            print_panel(f"[red]Error: Could not load selected protocol '{selected_protocol_name}' after selection.[/red]", title=error_title)
                            return None
                    except ProtocolNotFoundError:
                        # This case should ideally be caught by the name/number check above
                        print_panel(f"[yellow]Error: Protocol '{selected_protocol_name}' not found after selection. Please try again.[/yellow]", title=error_title)
                    except Exception as error:
                        get_console().print_exception()
                        print_panel(f"[red]An unexpected error occurred while loading '{selected_protocol_name}': {error}[/red]", title=error_title)
                        return None
        except ProtocolError as error: # Catch errors from self.list_protocols() itself
            # Error already printed by ProtocolError.__init__
            # get_console().print(f"[bold red]Protocol Selection Error:[/bold red] {error.message}", style="bold yellow")
            return None
        except Exception as error:
            get_console().print_exception()
            print_panel(f"[red]An unexpected error occurred during protocol selection: {error}[/red]", title="Selection Error")
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

    def _update_current_protocol_file(self, protocol_name: str) -> None:
        """Update the current protocol file with the name of the active protocol.

        Args:
            protocol_name: Name of the protocol to set as active
        """
        try:
            current_protocol_file = path_manager.erasmus_dir / "current_protocol.txt"
            current_protocol_file.write_text(protocol_name)
            logger.debug(f"Updated current_protocol.txt with '{protocol_name}'")
        except Exception as error:
            logger.error(f"Failed to update current protocol file: {error}")
            raise ProtocolError(f"Failed to update current protocol file: {error}")

def get_protocol_manager() -> ProtocolManager:
    return ProtocolManager()
"""
CLI commands for managing protocols.
"""

import os
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from erasmus.protocol import ProtocolManager, ProtocolError
from erasmus.utils.paths import get_path_manager
from erasmus.utils.rich_console import get_console, get_console_logger, print_panel, print_table

path_manager = get_path_manager()
protocol_manager = ProtocolManager()
protocol_app = typer.Typer(help="Manage development protocols.")

logger = get_console_logger()
def show_protocol_help_and_exit():
    """Show help information for protocol commands and exit."""
    command_rows = [
        ["erasmus protocol list", "List all available protocols (user and template)"],
        ["erasmus protocol create", "Create a new user protocol"],
        ["erasmus protocol show", "Display details of a specific protocol"],
        ["erasmus protocol edit", "Edit an existing user protocol"],
        ["erasmus protocol delete", "Remove a user protocol"],
        ["erasmus protocol load", "Load a protocol and update rules"],
        ["erasmus protocol select", "Interactively select and display a protocol"],
    ]
    
    console = Console()
    table = Table(title="Protocol Management Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="magenta")
    
    for command, description in command_rows:
        table.add_row(command, description)
    
    console.print(table)
    
    # Additional helpful information
    console.print("\n[bold]Important Notes:[/bold]")
    console.print("[yellow]• Template protocols cannot be deleted or modified[/yellow]")
    console.print("[yellow]• Use 'load' to update rules with a selected protocol[/yellow]")
    
    typer.echo("\nFor detailed help on a specific command, run:")
    typer.echo("  erasmus protocol <command> --help")
    raise typer.Exit(1)



@protocol_app.callback(invoke_without_command=True)
def protocol_callback(ctx: typer.Context):
    """
    Manage development protocols.
    """
    if ctx.invoked_subcommand is None:
        command_rows = [
            ["erasmus protocol list", "List all available protocols (user and template)"],
            ["erasmus protocol create", "Create a new user protocol"],
            ["erasmus protocol show", "Display details of a specific protocol"],
            ["erasmus protocol edit", "Edit an existing user protocol"],
            ["erasmus protocol delete", "Remove a user protocol"],
            ["erasmus protocol load", "Load a protocol and update rules"],
            ["erasmus protocol select", "Interactively select and display a protocol"],
        ]
        # Use Rich table for displaying commands
        console = Console()
        table = Table(title="Available Protocol Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="magenta")
        
        for command, description in command_rows:
            table.add_row(command, description)
        
        console.print(table)
        
        typer.echo("\nFor more information about a command, run:")
        typer.echo("  erasmus protocol <command> --help")
        raise typer.Exit(0)


@protocol_app.command()
def create(
    name: str = typer.Argument(None, help="Name of the protocol to create"),
    content: str = typer.Argument(None, help="Content of the protocol"),
):
    """Create a new protocol.

    This command creates a new protocol file with optional content.
    The protocol name will be sanitized to ensure it's safe for filesystem operations.
    """
    try:
        # Interactive name selection if not provided
        if not name:
            name = typer.prompt("Enter the protocol name")
        
        # Ensure name is not empty
        while not name:
            name = typer.prompt("Protocol name is required")
        
        # Interactive content selection if not provided
        if not content:
            content = typer.prompt("Enter the protocol content (leave blank to use template)", default="")
        
        # Create protocol using protocol manager
        protocol = protocol_manager.create_protocol(name, content)
        
        # Display success message
        print_panel(
            content=f"""[bold green]Protocol Created[/bold green]\n[cyan]Name:[/cyan] {protocol.name}\n[cyan]Path:[/cyan] {protocol.path}""",
            title="Protocol Creation",
            style="bold blue"
        )
        
        raise typer.Exit(0)
    except ProtocolError as error:
        get_console().print_exception()
        show_protocol_help_and_exit()

@protocol_app.command()
def delete(name: str = typer.Argument(None, help="Name of the protocol to delete")):
    """Delete a protocol.

    This command permanently removes a protocol file.
    Use with caution as this action cannot be undone.
    """
    try:
        # Interactive protocol selection if no name provided
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_panel(
                    content="[yellow]No protocols available for deletion.[/yellow]", 
                    title="Protocol Deletion", 
                    style="bold yellow"
                )
                raise typer.Exit(1)
            
            # Display protocols with indices
            protocol_rows = [[str(index + 1), detail['name']] for index, detail in enumerate(protocols)]
            print_table(
                ["#", "Protocol Name"], 
                protocol_rows, 
                title="Available Protocols for Deletion"
            )
            
            # Prompt for selection
            choice = typer.prompt("Select a protocol to delete by number or name")
            name_to_delete: str | None = None
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(protocols):
                    name_to_delete = protocols[idx]['name']
                else:
                    print_panel(f"[yellow]Invalid number: {choice}. Please select from the list.[/yellow]", title="Invalid Selection")
                    raise typer.Exit(1)
            else: # User entered a name
                normalized_choice = choice.removesuffix('.md')
                found_protocols = [p['name'] for p in protocols if p['name'].removesuffix('.md') == normalized_choice]
                if len(found_protocols) == 1:
                    name_to_delete = found_protocols[0]
                elif len(found_protocols) > 1:
                    print_panel(f"[yellow]Ambiguous name: '{choice}'. Multiple matches. Please be more specific or use number.[/yellow]", title="Invalid Selection")
                    raise typer.Exit(1)
                else:
                    print_panel(f"[yellow]Invalid name: '{choice}'. Not found in the list.[/yellow]", title="Invalid Selection")
                    raise typer.Exit(1)
            
            if not name_to_delete:
                # This case should not be reached if validation above is correct
                print_panel("[yellow]No protocol selected for deletion or invalid input.[/yellow]", title="Deletion Error")
                raise typer.Exit(1)
            name = name_to_delete # Assign to name variable used by subsequent logic
        
        try:
            # Delete protocol
            protocol_manager.delete_protocol(name)
            
            # Display success message
            print_panel(
                content=f"[bold red]Protocol Deleted[/bold red]\n[cyan]Name:[/cyan] {name}", 
                title="Protocol Deletion", 
                style="bold red"
            )
            
            raise typer.Exit(0)
        except PermissionError:
            # Handle template protocol deletion attempt
            print_panel(
                content=f"[yellow]Cannot delete template protocol: {name}[/yellow]\n[cyan]Tip:[/cyan] Template protocols are protected and cannot be deleted.", 
                title="Deletion Prevented", 
                style="bold yellow"
            )
            raise typer.Exit(1)
    except (ProtocolError, FileNotFoundError) as error:
        get_console().print_exception()
        raise typer.Exit(1)

@protocol_app.command()
def list():
    """List all protocols.

    This command shows all available protocols and their basic information.
    Use 'show' to view detailed information about a specific protocol.
    """
    try:
        # List protocols using protocol manager
        protocols = protocol_manager.list_protocols()
        
        if protocols:
            # Display protocols in a table
            protocol_rows = [[detail['name']] for detail in protocols]
            print_table(["Protocol Name"], protocol_rows, title="Available Protocols")
        else:
            print_panel("[yellow]No protocols found.[/yellow]", title="Protocols")
    except ProtocolError as error:
        get_console().print_exception()
        show_protocol_help_and_exit()


@protocol_app.command()
def show(name: str = typer.Argument(None, help="Name of the protocol to show")):
    """Show details of a protocol.

    This command displays detailed information about a specific protocol,
    including its content and metadata.
    """
    try:
        # If no name provided, interactively select a protocol
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_panel(
                    "[yellow]No protocols available.[/yellow]", 
                    title="Protocol Show", 
                    border_style="bold yellow"
                )
                raise typer.Exit(1)
            
            # Display protocols with indices
            protocol_rows = [[str(index + 1), protocol] for index, protocol in enumerate(protocols)]
            print_table(
                ["#", "Protocol Name"], 
                protocol_rows, 
                title="Available Protocols"
            )
            
            # Prompt for selection
            choice = typer.prompt("Select a protocol to show by number or name")
            name = protocols[int(choice) - 1] if choice.isdigit() and 1 <= int(choice) <= len(protocols) else choice
        
        # Load and display protocol details
        protocol = protocol_manager.load_protocol(name)
        
        # Display protocol details using rich console
        print_panel(
            f"[bold green]Protocol Details[/bold green]\n"
            f"[cyan]Name:[/cyan] {protocol.name}\n"
            f"[cyan]Path:[/cyan] {protocol.path}\n"
            f"[cyan]Content:[/cyan]\n{protocol.content}", 
            title="Protocol Information", 
            border_style="bold blue"
        )
        
        raise typer.Exit(0)
    except ProtocolError as error:
        get_console().print_exception()
        raise typer.Exit(1)


@protocol_app.command("select")
def select_protocol():
    """Interactively select a protocol, display its details, and update the rules file with it."""
    try:
        # MODIFICATION: Call the interactive selector from ProtocolManager
        # This will handle listing, table display, and prompting.
        # It returns the selected protocol name and also loads it into protocol_manager.protocol
        selected_name = protocol_manager.select_protocol_interactively(
            prompt_title="Select Protocol",
            error_title="Protocol Selection Failed"
        )

        # The protocol is already loaded by select_protocol_interactively into protocol_manager.protocol
        protocol = protocol_manager.protocol
        if not protocol or str(protocol) != selected_name:
            logger.error(f"Protocol '{selected_name}' not loaded correctly by interactive selection. Attempting explicit load.")
            protocol = protocol_manager._load_protocol(selected_name) # Attempt to load it explicitly
            if not protocol:
                 print_panel(f"[bold red]Error: Failed to load details for selected protocol: {selected_name}[/bold red]", title="Error", border_style="red")
                 raise typer.Exit(1)

        # Display protocol details using rich console
        # Ensure path is string and content preview is safe
        protocol_path_str = str(protocol.path) if protocol.path else "[Path not available]"
        protocol_content_preview = protocol.content[:200] if protocol.content else "[No Content]"
        if protocol.content and len(protocol.content) > 200:
            protocol_content_preview += "..."
            
        print_panel(
            f"[bold green]Selected Protocol[/bold green]\\n"
            f"[cyan]Name:[/cyan] {protocol.name}\\n"
            f"[cyan]Path:[/cyan] {protocol_path_str}\\n"
            f"[cyan]Content Preview (first 200 chars):[/cyan]\\n{protocol_content_preview}",
            title="Protocol Details",
            border_style="bold blue"
        )

        # FIX: Update the rules file using protocol_manager._update_context()
        if hasattr(protocol_manager, '_update_context') and callable(getattr(protocol_manager, '_update_context')):
            print_panel("Updating context and rules file...", title="Context Update", style="bold yellow", border_style="yellow")
            try:
                protocol_manager._update_context() # This uses the loaded protocol
                print_panel(f"Successfully updated rules file with protocol: {protocol.name}", title="Rules File Updated", style="bold green", border_style="green")
            except Exception as update_error:
                get_console().print_exception()
                print_panel(f"[bold red]Error during rules file update: {update_error}[/bold red]", title="Error", border_style="red")
                # Optionally, raise typer.Exit(1) or allow command to finish with error message
        else:
            print_panel("[bold yellow]Warning: Automated rules file update mechanism ('_update_context') not found in ProtocolManager.[/bold yellow]", title="Rules File Update", border_style="yellow")
        
        # typer.Exit(0) is not strictly necessary here, successful completion implies exit 0

    except ProtocolError:  # ProtocolError already prints itself via its __init__
        raise typer.Exit(1) # Exit with error code
    except Exception as error: # Catch any other unexpected errors
        get_console().print_exception()
        print_panel(f"[bold red]An unexpected error occurred in 'select' command: {error}[/bold red]", title="Error", border_style="red")
        raise typer.Exit(1)


@protocol_app.command("load")
def load_protocol(
    name: str = typer.Argument(None, help="Name of the protocol to load"),
):
    """Interactively select and load a protocol, merging it into the rules file with current context."""
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(["Info"], [["No protocols found"]], title="Available Protocols")
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name] for index, protocol_name in enumerate(protocols)
            ]
            print_table(["#", "Protocol Name"], protocol_rows, title="Available Protocols")
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
                    title="Protocol Select Failed",
                )
                raise typer.Exit(1)
            name = selected
        
        from erasmus.protocol import ProtocolManager
        protocol_manager = ProtocolManager()
        
        # Load the protocol
        protocol = protocol_manager.load_protocol(name)
        
        print_table(
            ["Info"],
            [[f"Updated rules file with protocol: {name}"]],
            title="Rules File Updated",
        )
        
        raise typer.Exit(0)
    except ProtocolError as exception:
        print_table(["Error"], [[str(exception)]], title="Protocol Select Failed")
        raise typer.Exit(1)


@protocol_app.command()
def edit(
    name: str = typer.Argument(None, help="Name of the protocol to edit"),
    editor: str = typer.Argument(None, help="Editor to use for editing"),
):
    """Edit a protocol file in your default editor (or specified editor)."""
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(["Info"], [["No protocols found"]], title="Available Protocols")
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name] for index, protocol_name in enumerate(protocols)
            ]
            print_table(["#", "Protocol Name"], protocol_rows, title="Available Protocols")
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
                    title="Protocol Edit Failed",
                )
                raise typer.Exit(1)
            name = selected
        protocol = protocol_manager.get_protocol(name)
        if not protocol:
            print_table(
                ["Error"],
                [[f"Protocol not found: {name}"]],
                title="Protocol Edit Failed",
            )
            raise typer.Exit(1)
        file_path = protocol.path
        editor_cmd = editor or os.environ.get("EDITOR", "nano")
        os.system(f"{editor_cmd} {file_path}")
        print_table(["Info"], [[f"Edited protocol: {name}"]], title="Protocol Edited")
        raise typer.Exit(0)
    except ProtocolError as error:
        print_table(["Error"], [[str(error)]], title="Protocol Edit Failed")
        raise typer.Exit(1)

if __name__ == "__main__":
    try:
        protocol_app()
    except Exception as error:
        print_table(["Error"], [[str(error)]], title="CLI Error")
        raise typer.Exit(1)

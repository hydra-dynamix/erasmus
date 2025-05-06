import typer
import re
import os
import subprocess
from pathlib import Path
from erasmus.utils.paths import get_path_manager
from erasmus.protocol import ProtocolManager
from erasmus.utils.rich_console import print_table, print_panel, get_console, get_console_logger

logger = get_console_logger()

path_manager = get_path_manager()
ide_env = path_manager.ide

console = get_console()

setup_app = typer.Typer(help="Setup Erasmus: initialize project, environment, and context.")

@setup_app.command()
def check_mcp_server(
    server_type: str = typer.Option('github', help='Type of MCP server to check'),
    ide_env: str = ide_env.name
):
    """Check MCP server configuration and binary compatibility."""

    check_script_path = path_manager.check_binary_script
    if not check_script_path.exists():
        logger.warning(f'No MCP configuration found for {ide_env} at {path_manager.mcp_config_path}')
    else:
        logger.info(f'MCP configuration found at {path_manager.mcp_config_path}')
    
    # Run binary check script
    try:
        result = subprocess.run(
            [str(check_script_path)], 
            capture_output=True, 
            text=True, 
            check=True
        )
        logger.info(result.stdout)
    except subprocess.CalledProcessError as error:
        logger.error(f'Binary check failed:\n{error.stderr}')

def set_erasmus_path():
    import os

    shell = os.environ.get("SHELL", "").split("/")[-1]
    home = str(Path.home())
    added = False
    msg = ""
    erasmus_func = """erasmus() {
    if [ -f erasmus.py ]; then
        uv run erasmus.py "$@"
    else
        command erasmus "$@"
    fi
}"""
    erasmus_fish_func = """function erasmus
    if test -f erasmus.py
        uv run erasmus.py $argv
    else
        command erasmus $argv
    end
end"""
    if shell == "bash":
        rc = f"{home}/.bashrc"
        if not Path(rc).read_text(errors="ignore").find("erasmus()") >= 0:
            with open(rc, "a") as file_handle:
                file_handle.write(f"\n{erasmus_func}\n")
            msg = f"Added erasmus function to {rc}"
            added = True
    elif shell == "zsh":
        rc = f"{home}/.zshrc"
        if not Path(rc).read_text(errors="ignore").find("erasmus()") >= 0:
            with open(rc, "a") as file_handle:
                file_handle.write(f"\n{erasmus_func}\n")
            msg = f"Added erasmus function to {rc}"
            added = True
    elif shell == "fish":
        rc = f"{home}/.config/fish/config.fish"
        if not Path(rc).read_text(errors="ignore").find("function erasmus") >= 0:
            with open(rc, "a") as file_handle:
                file_handle.write(f"\n{erasmus_fish_func}\n")
            msg = f"Added erasmus function to {rc}"
            added = True
    elif shell in ("csh", "tcsh"):
        rc = f"{home}/.cshrc" if shell == "csh" else f"{home}/.tcshrc"
        if not Path(rc).read_text(errors="ignore").find("alias erasmus") >= 0:
            with open(rc, "a") as file_handle:
                file_handle.write(
                    '\nalias erasmus "if ( -f erasmus.py ) uv run erasmus.py !*; else command erasmus !*; endif"\n'
                )
            msg = f"Added erasmus alias to {rc}"
            added = True
    else:
        msg = f"Unsupported shell: {shell}. Please add the erasmus function to your shell rc file manually."
    if added:
        print(msg)
    else:
        print(msg or "erasmus function/alias already present in your shell rc file.")


@setup_app.callback(invoke_without_command=True)
def setup_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is not None:
        return
    """Interactive setup for Erasmus: configure IDE, project, context, and protocol."""
    # Step 1: Use path manager for IDE detection and prompting
    print_table(["Info"], [[f"IDE detected: {ide_env}"]], title="Setup")

    # Step 2: Ensure Erasmus directories exist
    path_manager.ensure_dirs()
    print_table(["Info"], [[f"Erasmus folders created in: {path_manager.erasmus_dir}"]], title="Setup")

    # Step 3: Set up shell integration
    set_erasmus_path()

    # Step 4: List available contexts and allow creating new
    contexts = [directory.name for directory in sorted(path_manager.get_context_dir().iterdir()) if directory.is_dir()]
    context_rows = [["0", "Create New Context"]] + [
        [str(i + 1), name] for i, name in enumerate(contexts)
    ]
    print_table(["#", "Context Name"], context_rows, title="Available Contexts")
    
    choice = typer.prompt("Select a context by number or name (0 to create new)")
    
    # Handle context selection
    if choice == "0":
        context_name = typer.prompt("Enter name for new context")
        if not context_name:
            print_table(["Error"], [["Context name is required"]], title="Setup Failed")
            raise typer.Exit(1)
    else:
        # Find existing context
        selected = None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(contexts):
                selected = contexts[idx - 1]
        else:
            if choice in contexts:
                selected = choice
        if not selected:
            print_table(["Error"], [[f"Invalid selection: {choice}"]], title="Setup Failed")
            raise typer.Exit(1)
        context_name = selected

    # Create or load context files
    ctx_dir = path_manager.get_context_dir() / context_name
    ctx_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up context files
    ctx_files = [
        (ctx_dir / '.ctx.architecture.md', path_manager.architecture_template),
        (ctx_dir / '.ctx.tasks.md', path_manager.tasks_template),
        (ctx_dir / '.ctx.progress.md', path_manager.progress_template)
    ]
    
    for target_file, template_file in ctx_files:
        if not target_file.exists():
            if template_file.exists():
                content = template_file.read_text()
                # Replace title in template
                content = re.sub(r'<Title>.*?</Title>', f'<Title>{context_name}</Title>', content)
                content = re.sub(r'^# [^\n]*', f'# {context_name}', content)
            else:
                # Default content with title
                file_type = target_file.stem.split('.')[-1]
                content = f'# {context_name} {file_type.capitalize()}\n\n'
                if file_type == 'tasks':
                    content += '- [ ] Initial project setup\n'
                elif file_type == 'progress':
                    content += '## Current Sprint\n\n- Project initialized\n'
                elif file_type == 'architecture':
                    content += 'Define your system architecture here.\n'
            target_file.write_text(content)
    
    # Copy context files to root
    for ctx_file in ctx_files:
        target = Path(ctx_file[0].name)
        if ctx_file[0].exists():
            target.write_text(ctx_file[0].read_text())
    
    print_table(["Info"], [[f"Context {context_name} set up and loaded"]], title="Setup")

    # Step 6: Select or Confirm Protocol and Update Rules
    protocol_manager = ProtocolManager() # This loads current_protocol.txt into protocol_manager.protocol_name and protocol_manager.protocol
    
    # protocol_manager.protocol_name will be None if current_protocol.txt doesn't exist or is empty
    # protocol_manager.protocol will be the loaded ProtocolModel if a valid protocol_name was found and loaded

    # Determine the prompt message for typer.confirm
    confirm_prompt_message = f"Current protocol is '{protocol_manager.protocol_name}'. Do you want to change it?"
    # Default for typer.confirm: False if a protocol is set, True if no protocol is set (i.e., force selection)
    confirm_default = False if protocol_manager.protocol_name else True

    if not protocol_manager.protocol_name or typer.confirm(confirm_prompt_message, default=confirm_default):
        if protocol_manager.protocol_name: # Only print if changing
            print_panel(f"Changing from current protocol: '{protocol_manager.protocol_name}'. Attempting to select a new protocol...", title="Protocol Selection", style="cyan")
        else:
            print_panel("No protocol currently set. Attempting to select a new protocol...", title="Protocol Selection", style="cyan")

        selected_protocol_model = protocol_manager.select_protocol_interactively(
            prompt_title="Select a Protocol for Setup",
            error_title="Protocol Selection Failed"
        )
        # select_protocol_interactively updates current_protocol.txt and sets protocol_manager.protocol

        if selected_protocol_model and selected_protocol_model.name:
            # Protocol successfully selected and loaded by select_protocol_interactively
            try:
                protocol_manager._update_context() # This uses the now-loaded protocol to update rules
                protocol_type = getattr(selected_protocol_model, 'type', 'N/A') 
                print_panel(f"Protocol successfully set to: {selected_protocol_model.name} ({protocol_type}) and rules updated.", title="Setup Info", style="bold green", border_style="green")
            except AttributeError as attr_error:
                get_console().print_exception()
                print_panel(f"Critical setup error: ProtocolManager is missing a required method for context update. ({attr_error})", title="Setup Error", style="bold red", border_style="red")
                raise typer.Exit(1)
            except Exception as e:
                get_console().print_exception()
                print_panel(f"Failed to update rules file with newly selected protocol '{selected_protocol_model.name}': {e}.", title="Setup Warning", style="bold red", border_style="red")
        else:
            # This means selection was cancelled or failed within select_protocol_interactively
            if protocol_manager.protocol_name: # If a protocol was set before attempting to change
                 print_panel(f"No new protocol selected. Existing protocol '{protocol_manager.protocol_name}' remains active. Ensuring rules are up to date.", title="Setup Info", style="yellow")
                 try:
                    # Ensure context is updated with the (still) current protocol
                    if protocol_manager.protocol: # It should be loaded
                        protocol_manager._update_context()
                        logger.info(f"Ensured rules file is consistent with existing protocol: {protocol_manager.protocol_name}")
                    else: # Should not happen if protocol_name is set and valid
                        print_panel(f"Could not re-verify existing protocol '{protocol_manager.protocol_name}' for rules update.", title="Setup Warning", style="bold red", border_style="red")
                 except Exception as e:
                    get_console().print_exception()
                    print_panel(f"Failed to ensure rules file update for existing protocol '{protocol_manager.protocol_name}': {e}.", title="Setup Warning", style="bold red", border_style="red")
            else: # No protocol was set, and selection failed/cancelled
                 print_panel("No protocol selected and no existing protocol was set. Setup might be incomplete without an active protocol.", title="Setup Warning", style="bold yellow", border_style="yellow")

    elif protocol_manager.protocol_name and protocol_manager.protocol:
        # Protocol is already set (protocol_manager.protocol_name is not None)
        # and user confirmed NOT to change it.
        # Ensure the context is updated with this existing, loaded protocol.
        print_panel(f"Keeping existing protocol: '{protocol_manager.protocol_name}'. Ensuring rules are up to date...", title="Protocol Confirmation", style="cyan")
        try:
            protocol_manager._update_context() # protocol_manager.protocol is already loaded
            logger.info(f"Ensured rules file is consistent with existing protocol: {protocol_manager.protocol_name}")
            print_panel(f"Rules file confirmed for protocol: {protocol_manager.protocol_name}.", title="Setup Info", style="bold green", border_style="green")
        except Exception as e:
            get_console().print_exception()
            print_panel(f"Failed to ensure rules file consistency for existing protocol '{protocol_manager.protocol_name}': {e}.", title="Setup Warning", style="bold red", border_style="red")
    else:
        # This case should ideally not be reached if logic is correct: a protocol name exists but model isn't loaded
        # Or no protocol name and user didn't want to select.
        if protocol_manager.protocol_name and not protocol_manager.protocol:
             print_panel(f"Warning: A current protocol '{protocol_manager.protocol_name}' is named but could not be loaded. Rules may not be updated.", title="Setup Warning", style="bold yellow", border_style="yellow")
        else: # No protocol name, and not selected
             print_panel("No protocol is active. Rules file will not be updated with protocol-specific content.", title="Setup Info", style="yellow")

    print_table(["Info"], [["Erasmus setup complete."]], title="Setup Success")
    raise typer.Exit(0)

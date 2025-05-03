import typer
import re
from pathlib import Path
from erasmus.utils.paths import get_path_manager
from erasmus.protocol import ProtocolManager
from erasmus.utils.rich_console import print_table, get_console

setup_app = typer.Typer(help="Setup Erasmus: initialize project, environment, and context.")

console = get_console()


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
            with open(rc, "a") as f:
                f.write(f"\n{erasmus_func}\n")
            msg = f"Added erasmus function to {rc}"
            added = True
    elif shell == "zsh":
        rc = f"{home}/.zshrc"
        if not Path(rc).read_text(errors="ignore").find("erasmus()") >= 0:
            with open(rc, "a") as f:
                f.write(f"\n{erasmus_func}\n")
            msg = f"Added erasmus function to {rc}"
            added = True
    elif shell == "fish":
        rc = f"{home}/.config/fish/config.fish"
        if not Path(rc).read_text(errors="ignore").find("function erasmus") >= 0:
            with open(rc, "a") as f:
                f.write(f"\n{erasmus_fish_func}\n")
            msg = f"Added erasmus function to {rc}"
            added = True
    elif shell in ("csh", "tcsh"):
        rc = f"{home}/.cshrc" if shell == "csh" else f"{home}/.tcshrc"
        if not Path(rc).read_text(errors="ignore").find("alias erasmus") >= 0:
            with open(rc, "a") as f:
                f.write(
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
    path_manager = get_path_manager()
    print_table(["Info"], [[f"IDE detected: {path_manager.ide.name}"]], title="Setup")

    # Step 2: Ensure Erasmus directories exist
    path_manager.ensure_dirs()
    print_table(["Info"], [[f"Erasmus folders created in: {path_manager.erasmus_dir}"]], title="Setup")

    # Step 3: Set up shell integration
    set_erasmus_path()

    # Step 4: List available contexts and allow creating new
    contexts = [d.name for d in sorted(path_manager.get_context_dir().iterdir()) if d.is_dir()]
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

    # Step 6: Prompt for protocol selection
    protocol_manager = ProtocolManager()
    protocols = protocol_manager.list_protocols()
    if not protocols:
        print_table(["Error"], [["No protocols found."]], title="Setup Failed")
        raise typer.Exit(1)
    protocol_rows = [[str(i + 1), p] for i, p in enumerate(protocols)]
    print_table(["#", "Protocol Name"], protocol_rows, title="Available Protocols")
    while True:
        choice = typer.prompt("Select a protocol by number or name")
        selected = None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(protocols):
                selected = protocols[idx - 1]
        elif choice in protocols:
            selected = choice
        if selected:
            # Write the selected protocol to current_protocol.txt using path manager
            current_protocol_path = path_manager.erasmus_dir / "current_protocol.txt"
            current_protocol_path.write_text(selected)
            print_table(["Info"], [[f"Protocol set to: {selected}"]], title="Setup")
            # Immediately update the rules file to reflect the selected protocol
            try:
                from erasmus.file_monitor import _merge_rules_file

                _merge_rules_file()
                print_table(
                    ["Info"],
                    [[f"Rules file updated with protocol: {selected}"]],
                    title="Setup",
                )
            except Exception as e:
                print_table(
                    ["Error"],
                    [[f"Failed to update rules file: {e}"]],
                    title="Setup Warning",
                )
            break
        print(f"Invalid selection: {choice}")

    print_table(["Info"], [["Erasmus setup complete."]], title="Setup Success")
    raise typer.Exit(0)

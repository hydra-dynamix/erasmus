import typer
from pathlib import Path
from erasmus.utils.paths import get_path_manager
from erasmus.protocol import ProtocolManager
from erasmus.context import ContextManager
from erasmus.utils.rich_console import print_table

app = typer.Typer(help="Setup Erasmus: initialize project, environment, and context.")


@app.callback(invoke_without_command=True)
def setup_callback(ctx: typer.Context):
    if ctx.invoked_subcommand is not None:
        return
    """Interactive setup for Erasmus: configure IDE, project, context, and protocol."""
    # Step 1: Use path manager for IDE detection and prompting
    path_manager = get_path_manager()
    print_table(["Info"], [[f"IDE detected: {path_manager.ide.name}"]], title="Setup")

    # Step 2: Prompt for project name
    project_name = typer.prompt("Enter the project name")
    if not project_name:
        print_table(["Error"], [["Project name is required."]], title="Setup Failed")
        raise typer.Exit(1)

    # Step 3: Create project directory and context using path manager
    project_dir = Path.cwd() / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    print_table(["Info"], [[f"Project directory created: {project_dir}"]], title="Setup")

    # Step 4: Use path manager for all Erasmus folders inside project
    erasmus_dir = path_manager.erasmus_dir
    context_dir = path_manager.context_dir
    protocol_dir = path_manager.protocol_dir
    template_dir = path_manager.template_dir
    for d in [erasmus_dir, context_dir, protocol_dir, template_dir]:
        d.mkdir(parents=True, exist_ok=True)
    print_table(["Info"], [[f"Erasmus folders created in: {erasmus_dir}"]], title="Setup")

    # Step 5: Create a template context in the context folder and update root .ctx.*.xml files
    context_manager = ContextManager(base_dir=str(context_dir))
    context_manager.create_context(project_name)
    print_table(["Info"], [[f"Template context created: {project_name}"]], title="Setup")
    # Load the new context to root .ctx.*.xml files
    context_manager.load_context(project_name)
    print_table(
        ["Info"],
        [[f"Root .ctx.*.xml files updated for: {project_name}"]],
        title="Setup",
    )

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

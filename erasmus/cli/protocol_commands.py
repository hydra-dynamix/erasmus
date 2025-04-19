"""
CLI commands for managing protocols.
"""

import typer
from pathlib import Path
from loguru import logger
from erasmus.protocol import ProtocolManager, ProtocolError
from erasmus.utils.rich_console import print_table
import os
import re

protocol_manager = ProtocolManager()
app = typer.Typer(help="Manage development protocols.")


def show_help_and_exit():
    """Show help menu and exit with error code."""
    command_rows = [
        ["erasmus protocol list", "List all protocols"],
        ["erasmus protocol create", "Create a new protocol"],
        ["erasmus protocol show", "Show protocol details"],
        ["erasmus protocol update", "Update a protocol"],
        ["erasmus protocol edit", "Edit a protocol"],
        ["erasmus protocol delete", "Delete a protocol"],
        ["erasmus protocol select", "Select and display a protocol"],
        ["erasmus protocol load", "Load a protocol as active"],
    ]
    print_table(
        ["Command", "Description"], command_rows, title="Available Protocol Commands"
    )
    typer.echo("\nFor more information about a command, run:")
    typer.echo("  erasmus protocol <command> --help")
    raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def protocol_callback(ctx: typer.Context):
    """
    Manage development protocols.
    """
    if ctx.invoked_subcommand is None:
        command_rows = [
            ["erasmus protocol list", "List all protocols"],
            ["erasmus protocol create", "Create a new protocol"],
            ["erasmus protocol show", "Show protocol details"],
            ["erasmus protocol update", "Update a protocol"],
            ["erasmus protocol edit", "Edit a protocol"],
            ["erasmus protocol delete", "Delete a protocol"],
            ["erasmus protocol select", "Select and display a protocol"],
            ["erasmus protocol load", "Load a protocol as active"],
        ]
        print_table(
            ["Command", "Description"],
            command_rows,
            title="Available Protocol Commands",
        )
        typer.echo("\nFor more information about a command, run:")
        typer.echo("  erasmus protocol <command> --help")
        raise typer.Exit(0)


@app.command()
def create(
    name: str = typer.Argument(None, help="Name of the protocol to create"),
    content: str = typer.Argument(None, help="Content of the protocol"),
):
    """Create a new protocol.

    This command creates a new protocol file with optional content.
    The protocol name will be sanitized to ensure it's safe for filesystem operations.
    """
    try:
        if not name:
            name = typer.prompt("Enter the protocol name")
        if not name:
            print_table(
                ["Error"],
                [["Protocol name is required."]],
                title="Protocol Creation Failed",
            )
            raise typer.Exit(1)
        if content is None:
            content = typer.prompt(
                "Enter the protocol content (leave blank to use template)"
            )
        protocol_manager.create_protocol(name, content)
        logger.info(f"Created protocol: {name}")
        print_table(["Info"], [[f"Created protocol: {name}"]], title="Protocol Created")
        raise typer.Exit(0)
    except ProtocolError as e:
        logger.error(f"Failed to create protocol: {e}")
        show_help_and_exit()


@app.command()
def update(
    name: str = typer.Argument(None, help="Name of the protocol to update"),
    content: str = typer.Argument(None, help="New content for the protocol"),
):
    """Update an existing protocol.

    This command updates the content of an existing protocol.
    The protocol must exist before it can be updated.
    """
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(
                    ["Info"], [["No protocols found"]], title="Available Protocols"
                )
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name]
                for index, protocol_name in enumerate(protocols)
            ]
            print_table(
                ["#", "Protocol Name"], protocol_rows, title="Available Protocols"
            )
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
                    title="Protocol Update Failed",
                )
                raise typer.Exit(1)
            name = selected
        if content is None:
            content = typer.prompt("Enter the new protocol content")
        if not content:
            print_table(
                ["Error"],
                [["Protocol content is required."]],
                title="Protocol Update Failed",
            )
            raise typer.Exit(1)
        protocol_manager.update_protocol(name, content)
        logger.info(f"Updated protocol: {name}")
        print_table(["Info"], [[f"Updated protocol: {name}"]], title="Protocol Updated")
        raise typer.Exit(0)
    except ProtocolError as e:
        logger.error(f"Failed to update protocol: {e}")
        show_help_and_exit()


@app.command()
def delete(name: str = typer.Argument(None, help="Name of the protocol to delete")):
    """Delete a protocol.

    This command permanently removes a protocol file.
    Use with caution as this action cannot be undone.
    """
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(
                    ["Info"], [["No protocols found"]], title="Available Protocols"
                )
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name]
                for index, protocol_name in enumerate(protocols)
            ]
            print_table(
                ["#", "Protocol Name"], protocol_rows, title="Available Protocols"
            )
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
                    title="Protocol Deletion Failed",
                )
                raise typer.Exit(1)
            name = selected
        protocol_manager.delete_protocol(name)
        logger.info(f"Deleted protocol: {name}")
        print_table(["Info"], [[f"Deleted protocol: {name}"]], title="Protocol Deleted")
        raise typer.Exit(0)
    except (ProtocolError, PermissionError, FileNotFoundError) as e:
        print_table(["Error"], [[str(e)]], title="Protocol Deletion Failed")
        raise typer.Exit(1)


@app.command()
def list():
    """List all protocols.

    This command shows all available protocols and their basic information.
    Use 'show' to view detailed information about a specific protocol.
    """
    try:
        protocols = protocol_manager.list_protocols()
        if not protocols:
            typer.echo("No protocols found")
            return

        # Display protocols in a table
        protocol_rows = [[protocol] for protocol in protocols]
        print_table(["Protocol Name"], protocol_rows, title="Available Protocols")
    except ProtocolError as e:
        logger.error(f"Failed to list protocols: {e}")
        show_help_and_exit()


@app.command()
def show(name: str = typer.Argument(None, help="Name of the protocol to show")):
    """Show details of a protocol.

    This command displays detailed information about a specific protocol,
    including its content and metadata.
    """
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(
                    ["Info"], [["No protocols found"]], title="Available Protocols"
                )
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name]
                for index, protocol_name in enumerate(protocols)
            ]
            print_table(
                ["#", "Protocol Name"], protocol_rows, title="Available Protocols"
            )
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
                    title="Protocol Show Failed",
                )
                raise typer.Exit(1)
            name = selected
        protocol = protocol_manager.get_protocol(name)
        if not protocol:
            print_table(
                ["Error"],
                [[f"Protocol not found: {name}"]],
                title="Protocol Show Failed",
            )
            raise typer.Exit(1)
        print_table(["Info"], [[f"Protocol: {name}"]], title="Protocol Details")
        typer.echo(f"Path: {protocol.path}")
        typer.echo(f"Content:\n{protocol.content}")
        raise typer.Exit(0)
    except ProtocolError as e:
        print_table(["Error"], [[str(e)]], title="Protocol Show Failed")
        raise typer.Exit(1)


@app.command("select")
def select_protocol():
    """Interactively select a protocol, display its details, and update the rules file with it."""
    try:
        protocols = protocol_manager.list_protocols()
        if not protocols:
            print_table(["Info"], [["No protocols found"]], title="Available Protocols")
            raise typer.Exit(1)
        protocol_rows = [
            [str(index + 1), protocol_name]
            for index, protocol_name in enumerate(protocols)
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
        protocol = protocol_manager.get_protocol(selected)
        if not protocol:
            print_table(
                ["Error"],
                [[f"Protocol not found: {selected}"]],
                title="Protocol Select Failed",
            )
            raise typer.Exit(1)
        print_table(
            ["Info"], [[f"Selected protocol: {selected}"]], title="Protocol Selected"
        )
        typer.echo(f"Path: {protocol.path}")
        typer.echo(f"Content:\n{protocol.content}")
        # Write the selected protocol name to .erasmus/current_protocol.txt
        from erasmus.utils.paths import get_path_manager

        path_manager = get_path_manager()
        current_protocol_path = Path(path_manager.erasmus_dir) / "current_protocol.txt"
        current_protocol_path.write_text(selected)
        # Also update the rules file as in load
        template_path = path_manager.template_dir / "meta_rules.xml"
        if not template_path.exists():
            print_table(
                ["Error"],
                [["meta_rules.xml template not found."]],
                title="Protocol Select Failed",
            )
            raise typer.Exit(1)
        meta_rules_content = template_path.read_text()
        architecture = (
            path_manager.get_architecture_file().read_text()
            if path_manager.get_architecture_file().exists()
            else ""
        )
        progress = (
            path_manager.get_progress_file().read_text()
            if path_manager.get_progress_file().exists()
            else ""
        )
        tasks = (
            path_manager.get_tasks_file().read_text()
            if path_manager.get_tasks_file().exists()
            else ""
        )
        meta_rules_content = meta_rules_content.replace(
            "<!--ARCHITECTURE-->\n  <!--/ARCHITECTURE-->", architecture
        )
        meta_rules_content = meta_rules_content.replace(
            "<!--PROGRESS-->\n  <!--/PROGRESS-->", progress
        )
        meta_rules_content = meta_rules_content.replace(
            "<!--TASKS-->\n  <!--/TASKS-->", tasks
        )
        meta_rules_content = meta_rules_content.replace(
            "<!--PROTOCOL-->\n  <!--/PROTOCOL-->", protocol.content
        )
        rules_file = path_manager.get_rules_file()
        if not rules_file:
            print_table(
                ["Error"],
                [["No rules file configured."]],
                title="Protocol Select Failed",
            )
            raise typer.Exit(1)
        rules_file.write_text(meta_rules_content)
        print_table(
            ["Info"],
            [[f"Updated rules file with protocol: {selected}"]],
            title="Rules File Updated",
        )
        raise typer.Exit(0)
    except ProtocolError as exception:
        print_table(["Error"], [[str(exception)]], title="Protocol Select Failed")
        raise typer.Exit(1)


@app.command("load")
def load_protocol(
    name: str = typer.Argument(None, help="Name of the protocol to load"),
):
    """Interactively select and load a protocol, merging it into the rules file with current context."""
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(
                    ["Info"], [["No protocols found"]], title="Available Protocols"
                )
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name]
                for index, protocol_name in enumerate(protocols)
            ]
            print_table(
                ["#", "Protocol Name"], protocol_rows, title="Available Protocols"
            )
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
                    title="Protocol Load Failed",
                )
                raise typer.Exit(1)
            name = selected
        protocol = protocol_manager.get_protocol(name)
        if not protocol:
            print_table(
                ["Error"],
                [[f"Protocol not found: {name}"]],
                title="Protocol Load Failed",
            )
            raise typer.Exit(1)
        # Write the selected protocol name to .erasmus/current_protocol.txt
        from erasmus.utils.paths import get_path_manager

        path_manager = get_path_manager()
        current_protocol_path = Path(path_manager.erasmus_dir) / "current_protocol.txt"
        current_protocol_path.write_text(name)
        # Load meta_rules.xml template
        template_path = path_manager.template_dir / "meta_rules.xml"
        if not template_path.exists():
            print_table(
                ["Error"],
                [["meta_rules.xml template not found."]],
                title="Protocol Load Failed",
            )
            raise typer.Exit(1)
        meta_rules_content = template_path.read_text()
        # Read current context files
        architecture = (
            path_manager.get_architecture_file().read_text()
            if path_manager.get_architecture_file().exists()
            else ""
        )
        progress = (
            path_manager.get_progress_file().read_text()
            if path_manager.get_progress_file().exists()
            else ""
        )
        tasks = (
            path_manager.get_tasks_file().read_text()
            if path_manager.get_tasks_file().exists()
            else ""
        )
        # Replace context and protocol blocks using regex for robustness
        meta_rules_content = re.sub(
            r"<!--ARCHITECTURE-->[\s\S]*?<!--/ARCHITECTURE-->",
            architecture,
            meta_rules_content,
        )
        meta_rules_content = re.sub(
            r"<!--PROGRESS-->[\s\S]*?<!--/PROGRESS-->", progress, meta_rules_content
        )
        meta_rules_content = re.sub(
            r"<!--TASKS-->[\s\S]*?<!--/TASKS-->", tasks, meta_rules_content
        )
        meta_rules_content = re.sub(
            r"<!--PROTOCOL-->[\s\S]*?<!--/PROTOCOL-->",
            protocol.content,
            meta_rules_content,
        )
        # Write to rules file
        rules_file = path_manager.get_rules_file()
        if not rules_file:
            print_table(
                ["Error"], [["No rules file configured."]], title="Protocol Load Failed"
            )
            raise typer.Exit(1)
        rules_file.write_text(meta_rules_content)
        print_table(
            ["Info"],
            [[f"Loaded protocol: {name} into rules file"]],
            title="Protocol Loaded",
        )
        raise typer.Exit(0)
    except ProtocolError as exception:
        print_table(["Error"], [[str(exception)]], title="Protocol Load Failed")
        raise typer.Exit(1)


@app.command()
def edit(
    name: str = typer.Argument(None, help="Name of the protocol to edit"),
    editor: str = typer.Argument(None, help="Editor to use for editing"),
):
    """Edit a protocol file in your default editor (or specified editor)."""
    try:
        if not name:
            protocols = protocol_manager.list_protocols()
            if not protocols:
                print_table(
                    ["Info"], [["No protocols found"]], title="Available Protocols"
                )
                raise typer.Exit(1)
            protocol_rows = [
                [str(index + 1), protocol_name]
                for index, protocol_name in enumerate(protocols)
            ]
            print_table(
                ["#", "Protocol Name"], protocol_rows, title="Available Protocols"
            )
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


@app.command("watch")
def watch_protocol():
    """Monitor .ctx.*.xml files for changes and update the rules file with the current protocol. Does NOT monitor the rules file itself."""
    import time
    from erasmus.utils.paths import get_path_manager
    from erasmus.protocol import ProtocolManager
    from erasmus.utils.rich_console import print_table

    path_manager = get_path_manager()
    protocol_manager = ProtocolManager()
    ctx_files = [
        path_manager.get_architecture_file(),
        path_manager.get_progress_file(),
        path_manager.get_tasks_file(),
    ]
    template_path = path_manager.template_dir / "meta_rules.xml"
    rules_file = path_manager.get_rules_file()
    current_protocol_path = Path(path_manager.erasmus_dir) / "current_protocol.txt"

    def get_protocol_name():
        if current_protocol_path.exists():
            return current_protocol_path.read_text().strip()
        protocols = protocol_manager.list_protocols()
        if not protocols:
            print_table(
                ["Error"], [["No protocols found."]], title="Protocol Watch Failed"
            )
            raise typer.Exit(1)
        protocol_rows = [[str(i + 1), p] for i, p in enumerate(protocols)]
        print_table(["#", "Protocol Name"], protocol_rows, title="Available Protocols")
        choice = typer.prompt("Select a protocol by number or name")
        selected = None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(protocols):
                selected = protocols[idx - 1]
        elif choice in protocols:
            selected = choice
        if not selected:
            print_table(
                ["Error"],
                [[f"Invalid selection: {choice}"]],
                title="Protocol Watch Failed",
            )
            raise typer.Exit(1)
        current_protocol_path.write_text(selected)
        return selected

    def merge_and_write():
        if not template_path.exists():
            print_table(
                ["Error"],
                [["meta_rules.xml template not found."]],
                title="Protocol Watch Failed",
            )
            return
        meta_rules_content = template_path.read_text()
        architecture = ctx_files[0].read_text() if ctx_files[0].exists() else ""
        progress = ctx_files[1].read_text() if ctx_files[1].exists() else ""
        tasks = ctx_files[2].read_text() if ctx_files[2].exists() else ""
        meta_rules_content = re.sub(
            r"<!--ARCHITECTURE-->[\s\S]*?<!--/ARCHITECTURE-->",
            architecture,
            meta_rules_content,
        )
        meta_rules_content = re.sub(
            r"<!--PROGRESS-->[\s\S]*?<!--/PROGRESS-->", progress, meta_rules_content
        )
        meta_rules_content = re.sub(
            r"<!--TASKS-->[\s\S]*?<!--/TASKS-->", tasks, meta_rules_content
        )
        protocol_name = get_protocol_name()
        protocol = protocol_manager.get_protocol(protocol_name)
        if not protocol:
            print_table(
                ["Error"],
                [[f"Protocol not found: {protocol_name}"]],
                title="Protocol Watch Failed",
            )
            return
        meta_rules_content = re.sub(
            r"<!--PROTOCOL-->[\s\S]*?<!--/PROTOCOL-->",
            protocol.content,
            meta_rules_content,
        )
        if not rules_file:
            print_table(
                ["Error"],
                [["No rules file configured."]],
                title="Protocol Watch Failed",
            )
            return
        rules_file.write_text(meta_rules_content)
        print_table(
            ["Info"],
            [[f"Rules file updated with protocol: {protocol_name}"]],
            title="Rules File Updated",
        )

    # Track last modification times for only the .ctx.*.xml files
    last_mtimes = [f.stat().st_mtime if f.exists() else 0 for f in ctx_files]
    print_table(
        ["Info"], [["Watching .ctx.*.xml files for changes..."]], title="Protocol Watch"
    )
    try:
        while True:
            changed = False
            for i, f in enumerate(ctx_files):
                if f.exists():
                    mtime = f.stat().st_mtime
                    if mtime != last_mtimes[i]:
                        changed = True
                        last_mtimes[i] = mtime
            if changed:
                merge_and_write()
            time.sleep(1)
    except KeyboardInterrupt:
        print_table(
            ["Info"], [["Stopped watching context files."]], title="Protocol Watch"
        )


if __name__ == "__main__":
    try:
        app()
    except Exception as error:
        print_table(["Error"], [[str(error)]], title="CLI Error")
        raise typer.Exit(1)

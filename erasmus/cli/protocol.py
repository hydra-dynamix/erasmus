"""Protocol management commands for Erasmus.

This module provides Click-based commands for managing protocols in Erasmus.
"""

import json
import os
from pathlib import Path

import click
from rich.console import Console
import asyncio

from erasmus.utils.paths import SetupPaths
from erasmus.utils.logging import get_logger, LogContext
from erasmus.utils.protocols.manager import ProtocolManager
from erasmus.utils.context import update_context, scrub_non_ascii

logger = get_logger(__name__)
console = Console()

# Global protocol manager instance
protocol_manager = None


async def get_protocol_manager() -> ProtocolManager:
    """Get or create the protocol manager instance."""
    global protocol_manager
    if protocol_manager is None:
        protocol_manager = ProtocolManager()
        await protocol_manager.load_registry()
        protocol_manager.register_default_prompts()  # Register default prompts
    return protocol_manager


@click.group()
def protocol():
    """Protocol management commands."""
    pass


@protocol.command()
def list():
    """List all available protocols."""
    with LogContext(logger, "list_protocols"):
        asyncio.run(_list_protocols())


async def _list_protocols():
    """Async implementation of list command."""
    manager = await get_protocol_manager()

    protocols = manager.list_protocols()
    if not protocols:
        console.print("No protocols available.")
        return

    table = click.style("\nAvailable Protocols:", bold=True)
    for protocol in protocols:
        table += f"\n- {protocol.name} ({protocol.role})"
        table += f"\n  Triggers: {', '.join(protocol.triggers)}"
        table += f"\n  Produces: {', '.join(protocol.produces)}"
        table += f"\n  Consumes: {', '.join(protocol.consumes)}\n"

    console.print(table)


@protocol.command()
@click.argument("name")
def restore(name: str):
    """Restore a protocol by name."""
    with LogContext(logger, "restore_protocol"):
        asyncio.run(_restore_protocol(name))


async def _restore_protocol(name: str):
    """Async implementation of restore command."""
    manager = await get_protocol_manager()

    try:
        # Get the protocol
        protocol = manager.get_protocol(name)
        if not protocol:
            console.print(f"❌ Protocol not found: {name}", style="red")
            return

        # Update the context with the protocol
        update_context_with_protocol(name, manager)
        console.print(f"✅ Restored protocol: {name}")
    except Exception as e:
        console.print(f"❌ Error restoring protocol: {e}", style="red")


@protocol.command()
def select():
    """List available protocols and select one to load."""
    with LogContext(logger, "select_protocol"):
        asyncio.run(_select_protocol())


async def _select_protocol():
    """Async implementation of select command."""
    manager = await get_protocol_manager()

    protocols = manager.list_protocols()
    if not protocols:
        console.print("No protocols available to select.")
        return

    console.print("\nAvailable Protocols:")
    for i, protocol in enumerate(protocols, 1):
        console.print(f"{i}. {protocol.name} ({protocol.role})")

    try:
        selection = click.prompt("\nSelect a protocol (number)", type=int)
        if selection < 1 or selection > len(protocols):
            console.print("Invalid selection.", style="red")
            return

        selected_protocol = protocols[selection - 1]
        update_context_with_protocol(selected_protocol.name, manager)
        console.print(f"✅ Selected protocol: {selected_protocol.name}")
    except click.Abort:
        console.print("Selection cancelled.")
    except Exception as e:
        console.print(f"❌ Error selecting protocol: {e}", style="red")


@protocol.command()
@click.argument("name")
def store(name: str):
    """Store a protocol in the protocol directory."""
    with LogContext(logger, "store_protocol"):
        asyncio.run(_store_protocol(name))


async def _store_protocol(name: str):
    """Async implementation of store command."""
    manager = await get_protocol_manager()

    try:
        # Get the protocol
        protocol = manager.get_protocol(name)
        if not protocol:
            console.print(f"❌ Protocol not found: {name}", style="red")
            return

        # Store the protocol
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        protocols_dir = setup_paths.protocols_dir / "stored"
        protocols_dir.mkdir(parents=True, exist_ok=True)

        protocol_file = protocols_dir / f"{name}.json"
        with open(protocol_file, "w") as f:
            json.dump(protocol.model_dump(), f, indent=2)

        console.print(f"✅ Stored protocol: {name}")
    except Exception as e:
        console.print(f"❌ Error storing protocol: {e}", style="red")


@protocol.command()
@click.argument("name")
def delete(name: str):
    """Delete a protocol from the protocol directory."""
    with LogContext(logger, "delete_protocol"):
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        protocols_dir = setup_paths.protocols_dir / "stored"
        protocol_file = protocols_dir / f"{name}.json"

        if not protocol_file.exists():
            console.print(f"❌ Protocol file not found: {protocol_file}", style="red")
            return

        try:
            os.remove(protocol_file)
            console.print(f"✅ Deleted protocol: {name}")
        except Exception as e:
            console.print(f"❌ Error deleting protocol: {e}", style="red")


@protocol.command()
@click.argument("name")
@click.option("--context", help="JSON string containing context for protocol execution")
def execute(name: str, context: str):
    """Execute a specific protocol."""
    with LogContext(logger, "execute_protocol"):
        asyncio.run(_execute_protocol(name, context))


async def _execute_protocol(name: str, context: str):
    """Async implementation of execute command."""
    manager = await get_protocol_manager()

    try:
        context_data = json.loads(context) if context else {}

        # Execute the protocol
        transitions = await manager.execute_protocol(name, context_data)

        # Get the protocol
        protocol = manager.get_protocol(name)
        if not protocol:
            console.print(f"❌ Protocol not found: {name}", style="red")
            return

        console.print(f"\nProtocol Execution Result:")
        console.print(f"Protocol: {name}")
        console.print(f"Next Transitions: {len(transitions)}")

        if transitions:
            console.print("\nNext Transitions:")
            for transition in transitions:
                console.print(
                    f"- {transition.from_agent} -> {transition.to_agent} ({transition.trigger})"
                )
    except Exception as e:
        console.print(f"❌ Error executing protocol: {e}", style="red")


@protocol.command()
@click.argument("name")
@click.option("--context", help="JSON string containing context for workflow execution")
def workflow(name: str, context: str):
    """Run a workflow starting from a specific protocol."""
    with LogContext(logger, "run_workflow"):
        asyncio.run(_run_workflow(name, context))


async def _run_workflow(name: str, context: str):
    """Async implementation of workflow command."""
    manager = await get_protocol_manager()

    try:
        context_data = json.loads(context) if context else {}

        # Run the workflow
        current_protocol = name
        context = context_data.copy()
        results = []

        while current_protocol:
            # Execute the current protocol
            transitions = await manager.execute_protocol(current_protocol, context)
            results.append({"protocol": current_protocol, "transitions": transitions})

            # Determine next protocol based on transitions
            if transitions:
                # For simplicity, just take the first transition
                next_transition = transitions[0]
                current_protocol = next_transition.to_agent
            else:
                current_protocol = None

        console.print(f"\nWorkflow Execution Result:")
        console.print(f"Starting Protocol: {name}")
        console.print(f"Total Steps: {len(results)}")

        console.print("\nWorkflow Steps:")
        for i, step in enumerate(results, 1):
            console.print(f"{i}. {step['protocol']}")
            console.print(f"   Next Transitions: {len(step['transitions'])}")
    except Exception as e:
        console.print(f"❌ Error running workflow: {e}", style="red")


def update_context_with_protocol(protocol_name: str, manager: ProtocolManager = None) -> None:
    """Update the context object in the IDE environment rules file with the protocol."""
    # Get the rules file path
    setup_paths = SetupPaths.with_project_root(Path.cwd())
    rules_path = setup_paths.rules_file

    # Create the file if it doesn't exist
    if not rules_path.exists():
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        with open(rules_path, "w") as f:
            json.dump({"protocols": [protocol_name]}, f, indent=2)
        logger.info(f"Created new rules file at {rules_path}")
        return

    # Read the existing rules
    try:
        with open(rules_path, "r") as f:
            rules = json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in rules file: {rules_path}")
        rules = {"protocols": []}

    # Update the protocols list
    if "protocols" not in rules:
        rules["protocols"] = []

    # Add the protocol as the first entry if it's not already there
    if protocol_name not in rules["protocols"]:
        rules["protocols"].insert(0, protocol_name)

    # Load markdown files into context
    try:
        # Add architecture if available
        architecture_path = setup_paths.markdown_files.architecture
        if architecture_path.exists():
            with open(architecture_path, "r") as f:
                rules["architecture"] = f.read()

        # Add progress if available
        progress_path = setup_paths.markdown_files.progress
        if progress_path.exists():
            with open(progress_path, "r") as f:
                rules["progress"] = f.read()

        # Add tasks if available
        tasks_path = setup_paths.markdown_files.tasks
        if tasks_path.exists():
            with open(tasks_path, "r") as f:
                rules["tasks"] = f.read()

        # Add protocol markdown if available
        # First try the exact protocol name
        protocol_md_path = setup_paths.protocols_dir / "stored" / f"{protocol_name}.md"

        # If not found, try to find a matching protocol file
        if not protocol_md_path.exists():
            # Get the protocol manager to find the correct file path
            if manager is None:
                import asyncio

                manager = asyncio.run(get_protocol_manager())

            # Get the protocol to find its file path
            protocol = manager.get_protocol(protocol_name)
            if protocol and hasattr(protocol, "file_path"):
                # Extract the filename from the file_path
                import os

                file_name = os.path.basename(protocol.file_path)
                protocol_md_path = setup_paths.protocols_dir / "stored" / file_name

        if protocol_md_path.exists():
            with open(protocol_md_path, "r") as f:
                rules["protocol_markdown"] = f.read()
                logger.info(f"Loaded protocol markdown from {protocol_md_path}")
        else:
            logger.warning(f"Protocol markdown file not found for {protocol_name}")
    except Exception as e:
        logger.error(f"Error loading markdown files: {e}")

    # Get the protocol manager to get additional protocol information
    try:
        if manager is None:
            # Only create a new event loop if we don't have a manager
            import asyncio

            manager = asyncio.run(get_protocol_manager())

        protocol = manager.get_protocol(protocol_name)
        if protocol:
            # Update the context with protocol information
            context = {
                "current_protocol": protocol_name,
                "protocol_role": protocol.role,
                "protocol_triggers": protocol.triggers,
                "protocol_produces": protocol.produces,
                "protocol_consumes": protocol.consumes,
            }

            # Scrub non-ASCII characters from context values
            scrubbed_context = {
                key: scrub_non_ascii(value) if isinstance(value, str) else value
                for key, value in context.items()
            }

            # Update the rules with the scrubbed context
            rules.update(scrubbed_context)
    except Exception as e:
        logger.error(f"Error getting protocol information: {e}")

    # Write the updated rules
    with open(rules_path, "w") as f:
        json.dump(rules, f, indent=2)

    logger.info(f"Updated rules file with protocol: {protocol_name}")


def get_ide_env_rules_path() -> Path:
    """Get the path to the IDE environment rules file."""
    # Use SetupPaths to get the correct rules file path based on IDE environment
    setup_paths = SetupPaths.with_project_root(Path.cwd())
    return setup_paths.rules_file

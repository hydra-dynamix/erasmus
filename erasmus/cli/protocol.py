"""Protocol management commands for Erasmus.

This module provides Click-based commands for managing protocols in Erasmus.
"""

import asyncio
import json
import os
from pathlib import Path

import click
from rich.console import Console
from dotenv import load_dotenv

from erasmus.core.context import ContextFileHandler
from erasmus.utils.logging import LogContext, get_logger
from erasmus.utils.paths import SetupPaths
from erasmus.utils.protocols.manager import ProtocolManager
from erasmus.utils.env_manager import EnvironmentManager

# Load environment variables
load_dotenv()

logger = get_logger(__name__)
console = Console()

# Initialize environment manager
env_manager = EnvironmentManager()
context_handler = ContextFileHandler(workspace_root=Path.cwd())

# Global protocol manager instance
protocol_manager = None


async def get_protocol_manager() -> ProtocolManager:
    """Get or create the protocol manager instance."""
    global protocol_manager
    if protocol_manager is None:
        protocol_manager = ProtocolManager()
        await protocol_manager.load_registry()
        await protocol_manager.register_default_prompts()  # Register default prompts
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
        table += f"\n- {protocol.get('name', 'Unknown')}"
        table += f"\n  Triggers: {', '.join(protocol.get('triggers', []))}"
        table += f"\n  Produces: {', '.join(protocol.get('produces', []))}"
        table += f"\n  Consumes: {', '.join(protocol.get('consumes', []))}\n"

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
        await update_context_with_protocol(name)
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
        console.print(f"{i}. {protocol.get('name', 'Unknown')}")

    try:
        selection = click.prompt("\nSelect a protocol (number)", type=int)
        if selection < 1 or selection > len(protocols):
            console.print("Invalid selection.", style="red")
            return

        selected_protocol = protocols[selection - 1]
        await update_context_with_protocol(selected_protocol.get("name"))
        console.print(f"✅ Selected protocol: {selected_protocol.get('name')}")
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

        # Convert protocol to a serializable dictionary
        protocol_dict = {}
        if hasattr(protocol, "model_dump"):
            protocol_dict = protocol.model_dump()
        else:
            protocol_dict = {
                "name": protocol.get("name", name),
                "description": protocol.get("description", ""),
                "file_path": str(protocol.get("file_path", "")),
            }

        # Ensure all paths are converted to strings
        for key, value in protocol_dict.items():
            if isinstance(value, Path):
                protocol_dict[key] = str(value)

        with open(protocol_file, "w") as f:
            json.dump(protocol_dict, f, indent=2)

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


async def update_context_with_protocol(protocol_name: str):
    """Update the context with the selected protocol."""
    manager = await get_protocol_manager()
    protocol_file = manager.get_protocol_file(protocol_name)
    selected_protocol = protocol_file.read_text()
    protocol = manager.get_protocol(protocol_name)

    if not selected_protocol:
        console.print(f"❌ Protocol not found: {protocol_name}", style="red")
        return False

    try:
        # Get current context
        context = context_handler.read_context()

        # Update only protocol-related fields
        context["current_protocol"] = selected_protocol
        context["protocol_triggers"] = protocol.get("triggers", [])
        context["protocol_produces"] = protocol.get("produces", [])
        context["protocol_consumes"] = protocol.get("consumes", [])
        context["protocol_markdown"] = protocol.get("markdown", "")

        # Store updated context
        context_handler.update_context(context)

        console.print(f"✅ Updated context with protocol: {protocol_name}")
        return True
    except Exception as e:
        console.print(f"❌ Error updating context: {e}", style="red")
        return False


def get_ide_env_rules_path() -> Path:
    """Get the path to the IDE environment rules file."""
    # Use SetupPaths to get the correct rules file path based on IDE environment
    setup_paths = SetupPaths.with_project_root(Path.cwd())
    return setup_paths.rules_file

"""Protocol management commands for Erasmus.

This module provides Click-based commands for managing protocols in Erasmus.
"""

import json
from pathlib import Path

import click
from rich.console import Console

from erasmus.utils.paths import SetupPaths
from erasmus.utils.logging import get_logger, LogContext
from erasmus.utils.protocols.integration import ProtocolIntegration

logger = get_logger(__name__)
console = Console()


@click.group()
def protocol():
    """Protocol management commands."""
    pass


@protocol.command()
def list():
    """List all available protocols."""
    with LogContext(logger, "list_protocols"):
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        protocol_integration = ProtocolIntegration(setup_paths)

        protocols = protocol_integration.list_protocols()
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
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        protocol_integration = ProtocolIntegration(setup_paths)

        try:
            protocol_integration.restore_protocol(name)
            console.print(f"✅ Restored protocol: {name}")
        except Exception as e:
            console.print(f"❌ Error restoring protocol: {e}", style="red")


@protocol.command()
def select():
    """List available protocols and select one to load."""
    with LogContext(logger, "select_protocol"):
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        protocol_integration = ProtocolIntegration(setup_paths)

        protocols = protocol_integration.list_protocols()
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
            protocol_integration.restore_protocol(selected_protocol.name)
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
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        protocol_integration = ProtocolIntegration(setup_paths)

        try:
            protocol_integration.store_protocol(name)
            console.print(f"✅ Stored protocol: {name}")
        except Exception as e:
            console.print(f"❌ Error storing protocol: {e}", style="red")


@protocol.command()
@click.argument("name")
def delete(name: str):
    """Delete a protocol from the protocol directory."""
    with LogContext(logger, "delete_protocol"):
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        protocol_integration = ProtocolIntegration(setup_paths)

        try:
            protocol_integration.delete_protocol(name)
            console.print(f"✅ Deleted protocol: {name}")
        except Exception as e:
            console.print(f"❌ Error deleting protocol: {e}", style="red")


@protocol.command()
@click.argument("name")
@click.option("--context", help="JSON string containing context for protocol execution")
def execute(name: str, context: str):
    """Execute a specific protocol."""
    with LogContext(logger, "execute_protocol"):
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        protocol_integration = ProtocolIntegration(setup_paths)

        try:
            context_data = json.loads(context) if context else {}
            result = protocol_integration.execute_protocol(name, context_data)

            console.print(f"\nProtocol Execution Result:")
            console.print(f"Protocol: {name}")
            console.print(f"Artifacts: {len(result['artifacts'])}")
            console.print(f"Next Transitions: {len(result['next_transitions'])}")

            if result["artifacts"]:
                console.print("\nArtifacts:")
                for artifact in result["artifacts"]:
                    console.print(f"- {artifact['name']} ({artifact['type']})")

            if result["next_transitions"]:
                console.print("\nNext Transitions:")
                for transition in result["next_transitions"]:
                    console.print(
                        f"- {transition['from_agent']} -> {transition['to_agent']} "
                        f"({transition['trigger']})"
                    )
        except Exception as e:
            console.print(f"❌ Error executing protocol: {e}", style="red")


@protocol.command()
@click.argument("name")
@click.option("--context", help="JSON string containing context for workflow execution")
def workflow(name: str, context: str):
    """Run a workflow starting from a specific protocol."""
    with LogContext(logger, "run_workflow"):
        setup_paths = SetupPaths.with_project_root(Path.cwd())
        protocol_integration = ProtocolIntegration(setup_paths)

        try:
            context_data = json.loads(context) if context else {}
            result = protocol_integration.run_workflow(name, context_data)

            console.print(f"\nWorkflow Execution Result:")
            console.print(f"Starting Protocol: {name}")
            console.print(f"Total Steps: {len(result['workflow_results'])}")

            console.print("\nWorkflow Steps:")
            for i, step in enumerate(result["workflow_results"], 1):
                console.print(f"{i}. {step['protocol']}")
                console.print(f"   Artifacts: {len(step['result']['artifacts'])}")
                console.print(f"   Next Transitions: {len(step['result']['next_transitions'])}")
        except Exception as e:
            console.print(f"❌ Error running workflow: {e}", style="red")

"""Protocol CLI commands."""

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from erasmus.utils.paths import PathManager, SetupPaths
from erasmus.utils.protocols.manager import ProtocolManager
from erasmus.utils.protocols.server import ProtocolServer
from erasmus.utils.logging import get_logger
from .integration import ProtocolIntegration

logger = logging.getLogger(__name__)


def get_path_manager(project_root: Optional[Path] = None) -> PathManager:
    """Get a PathManager instance.

    Args:
        project_root: Optional project root path. If not provided, uses current directory.

    Returns:
        PathManager: A PathManager instance
    """
    return PathManager(project_root)


def handle_protocol_commands(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle protocol-related commands.

    Args:
        args: Command arguments

    Returns:
        Dict[str, Any]: Command results
    """
    path_manager = get_path_manager()
    path_manager.ensure_directories()

    # Initialize protocol integration
    protocol_manager = ProtocolManager()
    protocol_server = ProtocolServer(setup_paths=path_manager)

    # Register prompts
    protocol_manager.register_default_prompts()

    # Handle JSON context if provided
    context = {}
    if args.get("json_context"):
        try:
            context = json.loads(args["json_context"])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON context: {e}")
            return {"error": f"Invalid JSON context: {e}"}

    command = args.get("protocol_command")
    if not command:
        return {"error": "No protocol command specified"}

    try:
        if command == "list":
            # List available protocols
            protocols = protocol_manager.list_protocols()
            return {"protocols": protocols}

        elif command == "restore":
            # Restore protocol from backup
            protocol_name = args.get("protocol_name")
            if not protocol_name:
                return {"error": "Protocol name required for restore"}

            result = protocol_manager.restore_protocol(protocol_name)
            return {"result": result}

        elif command == "select":
            # Select a protocol
            protocol_name = args.get("protocol_name")
            if not protocol_name:
                return {"error": "Protocol name required for selection"}

            result = update_context_with_protocol(protocol_name, context)
            return {"result": result}

        elif command == "store":
            # Store a protocol
            protocol_name = args.get("protocol_name")
            if not protocol_name:
                return {"error": "Protocol name required for storage"}

            result = protocol_manager.store_protocol(protocol_name)
            return {"result": result}

        elif command == "delete":
            # Delete a protocol
            protocol_name = args.get("protocol_name")
            if not protocol_name:
                return {"error": "Protocol name required for deletion"}

            result = protocol_manager.delete_protocol(protocol_name)
            return {"result": result}

        elif command == "execute":
            # Execute a protocol
            protocol_name = args.get("protocol_name")
            if not protocol_name:
                return {"error": "Protocol name required for execution"}

            artifacts = protocol_server.execute_protocol(protocol_name, context)
            return {"artifacts": [artifact.model_dump() for artifact in artifacts]}

        elif command == "workflow":
            # Get protocol workflow
            protocol_name = args.get("protocol_name")
            if not protocol_name:
                return {"error": "Protocol name required for workflow"}

            workflow = protocol_server.get_protocol_workflow(protocol_name)
            return {"workflow": workflow}

        else:
            return {"error": f"Unknown protocol command: {command}"}

    except Exception as e:
        logger.error(f"Error handling protocol command {command}: {e}")
        return {"error": str(e)}


def update_context_with_protocol(protocol_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Update the context with the selected protocol.

    Args:
        protocol_name: Name of the protocol to select
        context: Current context

    Returns:
        Dict[str, Any]: Updated context
    """
    setup_paths = SetupPaths.with_project_root(Path.cwd())

    # Create rules file if it doesn't exist
    if not setup_paths.rules_file.exists():
        setup_paths.rules_file.touch()

    # Read existing rules
    try:
        with open(setup_paths.rules_file, "r") as f:
            rules = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        rules = {}

    # Update protocols list
    if "protocols" not in rules:
        rules["protocols"] = []

    if protocol_name not in rules["protocols"]:
        rules["protocols"].append(protocol_name)

    # Load protocol markdown if available
    protocol_file = setup_paths.protocols_dir / "stored" / f"{protocol_name}.md"
    if protocol_file.exists():
        with open(protocol_file, "r") as f:
            protocol_content = f.read()
            context["protocol_content"] = protocol_content

    # Write updated rules
    with open(setup_paths.rules_file, "w") as f:
        json.dump(rules, f, indent=2)

    return context


def add_protocol_commands(parser: argparse.ArgumentParser) -> None:
    """Add protocol-related commands to the argument parser."""
    # Create a subparser for protocol commands
    subparsers = parser.add_subparsers(dest="subcommand", help="Protocol management commands")

    # Protocol list command
    list_parser = subparsers.add_parser("list", help="List all available protocols")

    # Protocol restore command
    restore_parser = subparsers.add_parser("restore", help="Restore a protocol by name")
    restore_parser.add_argument("name", type=str, help="Name of the protocol to restore")

    # Protocol select command
    select_parser = subparsers.add_parser(
        "select", help="List available protocols and select one to load"
    )

    # Protocol store command
    store_parser = subparsers.add_parser("store", help="Store a protocol in the protocol directory")
    store_parser.add_argument("name", type=str, help="Name of the protocol to store")

    # Protocol delete command
    delete_parser = subparsers.add_parser(
        "delete", help="Delete a protocol from the protocol directory"
    )
    delete_parser.add_argument("name", type=str, help="Name of the protocol to delete")

    # Protocol execute command
    execute_parser = subparsers.add_parser("execute", help="Execute a specific protocol")
    execute_parser.add_argument("name", type=str, help="Name of the protocol to execute")
    execute_parser.add_argument(
        "--context", type=str, help="JSON string containing context for protocol execution"
    )

    # Protocol workflow command
    workflow_parser = subparsers.add_parser(
        "workflow", help="Run a workflow starting from a specific protocol"
    )
    workflow_parser.add_argument(
        "name", type=str, help="Name of the protocol to start the workflow from"
    )
    workflow_parser.add_argument(
        "--context", type=str, help="JSON string containing context for workflow execution"
    )


def get_ide_env_rules_path() -> Path:
    """Get the path to the IDE environment rules file."""
    from erasmus.utils.paths import SetupPaths

    # Use SetupPaths to get the correct rules file path based on IDE environment
    setup_paths = SetupPaths.with_project_root(Path.cwd())
    return setup_paths.rules_file


async def handle_protocol_commands(args: argparse.Namespace) -> None:
    """Handle protocol-related commands."""
    if not args.subcommand:
        return

    # Create setup paths
    setup_paths = SetupPaths.with_project_root(Path.cwd())

    # Initialize the protocol integration
    protocol_integration = ProtocolIntegration(setup_paths)
    await protocol_integration.initialize()

    # Register prompt functions
    protocol_integration.register_protocol_prompts()

    # Create protocols directory if it doesn't exist
    protocols_dir = setup_paths.protocols_dir / "stored"
    protocols_dir.mkdir(parents=True, exist_ok=True)

    # Load the registry
    registry_path = setup_paths.protocols_dir / "agent_registry.json"
    if not registry_path.exists():
        logger.error(f"Registry file not found: {registry_path}")
        return

    # Load the registry
    with open(registry_path, "r") as f:
        registry_data = json.load(f)

    # Parse context if provided
    context = {}
    if hasattr(args, "context") and args.context:
        try:
            context = json.loads(args.context)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in protocol context")
            return

    # Handle protocol list command
    if args.subcommand == "list":
        protocols = protocol_integration.list_protocols()
        print("\nAvailable Protocols:")
        for protocol in protocols:
            print(f"- {protocol.name} ({protocol.role})")
            print(f"  Triggers: {', '.join(protocol.triggers)}")
            print(f"  Produces: {', '.join(protocol.produces)}")
            print(f"  Consumes: {', '.join(protocol.consumes)}")
            print()

    # Handle protocol restore command
    elif args.subcommand == "restore":
        protocol_name = args.name
        protocol_file = protocols_dir / f"{protocol_name}.json"

        if not protocol_file.exists():
            logger.error(f"Protocol file not found: {protocol_file}")
            return

        try:
            with open(protocol_file, "r") as f:
                protocol_data = json.load(f)

            # Update the context with the protocol
            update_context_with_protocol(protocol_name, context)

            logger.info(f"Restored protocol: {protocol_name}")
        except Exception as e:
            logger.error(f"Error restoring protocol {protocol_name}: {e}")

    # Handle protocol select command
    elif args.subcommand == "select":
        # List available protocols
        available_protocols = []
        for agent in registry_data["agents"]:
            protocol_name = agent["name"]
            protocol_file = protocols_dir / f"{protocol_name}.json"
            if protocol_file.exists():
                available_protocols.append(protocol_name)

        if not available_protocols:
            logger.info("No protocols available to select")
            return

        # Display available protocols
        print("\nAvailable Protocols:")
        for i, protocol_name in enumerate(available_protocols):
            print(f"{i + 1}. {protocol_name}")

        # Get user input
        try:
            selection = int(input("\nSelect a protocol (number): "))
            if selection < 1 or selection > len(available_protocols):
                logger.error("Invalid selection")
                return

            selected_protocol = available_protocols[selection - 1]

            # Update the context with the selected protocol
            update_context_with_protocol(selected_protocol, context)

            logger.info(f"Selected protocol: {selected_protocol}")
        except ValueError:
            logger.error("Invalid input")

    # Handle protocol store command
    elif args.subcommand == "store":
        protocol_name = args.name

        # Find the protocol in the registry
        protocol_data = None
        for agent in registry_data["agents"]:
            if agent["name"] == protocol_name:
                protocol_data = agent
                break

        if not protocol_data:
            logger.error(f"Protocol not found in registry: {protocol_name}")
            return

        # Store the protocol
        protocol_file = protocols_dir / f"{protocol_name}.json"
        with open(protocol_file, "w") as f:
            json.dump(protocol_data, f, indent=2)

        logger.info(f"Stored protocol: {protocol_name}")

    # Handle protocol delete command
    elif args.subcommand == "delete":
        protocol_name = args.name
        protocol_file = protocols_dir / f"{protocol_name}.json"

        if not protocol_file.exists():
            logger.error(f"Protocol file not found: {protocol_file}")
            return

        try:
            os.remove(protocol_file)
            logger.info(f"Deleted protocol: {protocol_name}")
        except Exception as e:
            logger.error(f"Error deleting protocol {protocol_name}: {e}")

    # Handle protocol execute command
    elif args.subcommand == "execute":
        try:
            result = await protocol_integration.execute_protocol(args.name, context)
            print(f"\nProtocol Execution Result:")
            print(f"Protocol: {args.name}")
            print(f"Artifacts: {len(result['artifacts'])}")
            print(f"Next Transitions: {len(result['next_transitions'])}")

            # Print artifacts
            print("\nArtifacts:")
            for artifact in result["artifacts"]:
                print(f"- {artifact['name']} ({artifact['type']})")

            # Print transitions
            print("\nNext Transitions:")
            for transition in result["next_transitions"]:
                print(
                    f"- {transition['from_agent']} -> {transition['to_agent']} ({transition['trigger']})"
                )

        except Exception as e:
            logger.error(f"Error executing protocol {args.name}: {e}")

    # Handle protocol workflow command
    elif args.subcommand == "workflow":
        try:
            result = await protocol_integration.run_workflow(args.name, context)
            print(f"\nWorkflow Execution Result:")
            print(f"Starting Protocol: {args.name}")
            print(f"Total Steps: {len(result['workflow_results'])}")

            # Print workflow steps
            print("\nWorkflow Steps:")
            for i, step in enumerate(result["workflow_results"]):
                print(f"{i + 1}. {step['protocol']}")
                print(f"   Artifacts: {len(step['result']['artifacts'])}")
                print(f"   Next Transitions: {len(step['result']['next_transitions'])}")

        except Exception as e:
            logger.error(f"Error running workflow from {args.name}: {e}")

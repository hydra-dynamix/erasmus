import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from erasmus.utils.logging import get_logger
from erasmus.utils.paths import SetupPaths
from erasmus.utils.context import get_rules_path
from .manager import ProtocolManager

logger = get_logger(__name__)


def add_protocol_management_commands(parser: argparse.ArgumentParser) -> None:
    """Add protocol management commands to the argument parser."""
    protocol_group = parser.add_argument_group("Protocol Management Commands")

    # Restore protocol command
    protocol_group.add_argument(
        "--restore-protocol",
        type=str,
        help="Restore a protocol by name from the protocol directory",
    )

    # Select protocol command
    protocol_group.add_argument(
        "--select-protocol",
        action="store_true",
        help="List available protocols and select one to load",
    )

    # Store protocol command
    protocol_group.add_argument(
        "--store-protocol", type=str, help="Store the current protocol in the protocol directory"
    )

    # Delete protocol command
    protocol_group.add_argument(
        "--delete-protocol", type=str, help="Delete a protocol from the protocol directory"
    )


def update_context_with_protocol(protocol_name: str) -> None:
    """Update the context object in the IDE environment rules file with the protocol."""
    rules_path = get_rules_path()
    # Create the file if it doesn't exist
    if not rules_path.exists():
        rules_path.parent.mkdir(parent=True, exist_ok=True)
        rules_path.write_text(json.dumps({"protocols": [protocol_name]}, indent=2))
        logger.info(f"Created new rules file at {rules_path}")
        return

    # Read the existing rules
    try:
        rules = json.loads(rules_path.read_text())
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in rules file: {rules_path}")
        rules = {"protocols": []}

    # Update the protocols list
    if "protocols" not in rules:
        rules["protocols"] = []

    # Add the protocol as the first entry if it's not already there
    if protocol_name not in rules["protocols"]:
        rules["protocols"].insert(0, protocol_name)

    # Write the updated rules
    rules_path.write_text(json.dumps(rules, indent=2))

    logger.info(f"Updated rules file with protocol: {protocol_name}")


async def handle_protocol_management_commands(args: argparse.Namespace) -> None:
    """Handle protocol management commands."""
    if not (
        args.restore_protocol or args.select_protocol or args.store_protocol or args.delete_protocol
    ):
        return

    # Initialize the protocol manager
    protocol_manager = ProtocolManager()

    # Load the registry
    await protocol_manager.load_registry()

    # Create protocols directory if it doesn't exist
    protocols_dir = protocol_manager.setup_paths.protocols_dir / "stored"
    protocols_dir.mkdir(parents=True, exist_ok=True)

    # Handle restore protocol command
    if args.restore_protocol:
        protocol_name = args.restore_protocol
        protocol_file = protocols_dir / f"{protocol_name}.json"

        if not protocol_file.exists():
            logger.error(f"Protocol file not found: {protocol_file}")
            return

        try:
            protocol_data = json.loads(protocol_file.read_text())

            # Update the context with the protocol
            update_context_with_protocol(protocol_name)

            logger.info(f"Restored protocol: {protocol_name}")
        except Exception as e:
            logger.error(f"Error restoring protocol {protocol_name}: {e}")

    # Handle select protocol command
    if args.select_protocol:
        # List available protocols
        available_protocols = []
        for agent in protocol_manager.agents:
            protocol_name = agent.name
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
            update_context_with_protocol(selected_protocol)

            logger.info(f"Selected protocol: {selected_protocol}")
        except ValueError:
            logger.error("Invalid input")

    # Handle store protocol command
    if args.store_protocol:
        protocol_name = args.store_protocol

        # Find the protocol in the registry
        protocol_data = None
        for agent in protocol_manager.agents:
            if agent.name == protocol_name:
                protocol_data = agent
                break

        if not protocol_data:
            logger.error(f"Protocol not found in registry: {protocol_name}")
            return

        # Store the protocol
        protocol_file = protocols_dir / f"{protocol_name}.json"
        protocol_file.write_text(json.dumps(protocol_data, indent=2))

        logger.info(f"Stored protocol: {protocol_name}")

    # Handle delete protocol command
    if args.delete_protocol:
        protocol_name = args.delete_protocol
        protocol_file = protocols_dir / f"{protocol_name}.json"

        if not protocol_file.exists():
            logger.error(f"Protocol file not found: {protocol_file}")
            return

        try:
            protocol_file.unlink()
            logger.info(f"Deleted protocol: {protocol_name}")
        except Exception as e:
            logger.error(f"Error deleting protocol {protocol_name}: {e}")

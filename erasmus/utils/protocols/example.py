import asyncio
from pathlib import Path

from erasmus.utils.paths import SetupPaths
from erasmus.utils.logging import get_logger
from .integration import ProtocolIntegration

logger = get_logger(__name__)


# Example prompt functions for different protocols
def product_owner_prompt(context: dict) -> dict:
    """Example prompt function for the Product Owner Agent."""
    # In a real implementation, this would use your AI model or other logic
    return {
        "architecture.md": "# Project Architecture\n\nThis is a sample architecture document.",
        "progress.md": "# Development Progress\n\nCurrent progress: 0%",
    }


def developer_prompt(context: dict) -> dict:
    """Example prompt function for the Developer Agent."""
    # In a real implementation, this would use your AI model or other logic
    return {
        "tasks.md": "# Development Tasks\n\n1. Implement feature X\n2. Write tests\n3. Update documentation"
    }


async def run_protocol_example():
    """Run an example of the protocol system."""
    # Create setup paths
    setup_paths = SetupPaths.with_project_root(Path.cwd())

    # Initialize the protocol integration
    protocol_integration = ProtocolIntegration(setup_paths)
    await protocol_integration.initialize()

    # Register prompt functions
    protocol_integration.register_protocol_prompts()

    # Example: Execute a single protocol
    context = {
        "project_name": "Example Project",
        "description": "A sample project to demonstrate the protocol system",
    }

    try:
        # Execute the Product Owner Agent protocol
        result = await protocol_integration.execute_protocol("Product Owner Agent", context)
        logger.info(f"Product Owner Agent result: {result}")

        # Example: Run a workflow
        workflow_result = await protocol_integration.run_workflow("Product Owner Agent", context)
        logger.info(f"Workflow result: {workflow_result}")

    except Exception as e:
        logger.error(f"Error running protocol example: {e}")


if __name__ == "__main__":
    asyncio.run(run_protocol_example())

import json
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class GitHubMCPServerConfig:
    """Configuration loader for GitHub MCP Server."""
    
    def __init__(self):
        """
        Initialize the configuration loader.
        
        Args:
            config_path (str | Path, optional): Path to the configuration file. 
                Defaults to the default location in .erasmus/servers/github.
        """
        
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load the configuration from the JSON file.
        
        Returns:
            Dict[str, Any]: Loaded configuration dictionary
        """
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Configuration file not found at {self.config_path}")
            return {}
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in configuration file at {self.config_path}")
            return {}

    def get_tool_description(self, tool_name: str) -> str:
        """
        Get the description for a specific tool.
        
        Args:
            tool_name (str): Name of the tool to get description for.
        
        Returns:
            str: Tool description or an empty string if not found.
        """
        key = f"TOOL_{tool_name.upper()}_DESCRIPTION"
        return self._config.get(key, "")

    def get_resource_description(self, resource_name: str) -> str:
        """
        Get the description for a specific resource.
        
        Args:
            resource_name (str): Name of the resource to get description for.
        
        Returns:
            str: Resource description or an empty string if not found.
        """
        key = f"RESOURCE_{resource_name.upper()}_DESCRIPTION"
        return self._config.get(key, "")

    def get_all_tool_descriptions(self) -> Dict[str, str]:
        """
        Get all tool descriptions.
        
        Returns:
            Dict[str, str]: Dictionary of tool names and their descriptions.
        """
        return {
            key.replace('TOOL_', '').replace('_DESCRIPTION', ''): value
            for key, value in self._config.items()
            if key.startswith('TOOL_') and key.endswith('_DESCRIPTION')
        }

# Create a global instance for easy access
github_mcp_server_config = GitHubMCPServerConfig()

if __name__ == "__main__":
    # Demonstrate usage
    print("All Tool Descriptions:")
    for tool, desc in github_mcp_server_config.get_all_tool_descriptions().items():
        print(f"{tool}: {desc}")

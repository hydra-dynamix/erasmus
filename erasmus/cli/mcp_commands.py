"""
MCP CLI commands for managing MCP servers and clients.
"""
import os
import typer
import inspect

from pathlib import Path
from pydantic import BaseModel
from erasmus.mcp.registry import McpRegistry
from erasmus.mcp.models import McpError        # Restored McpError import
from erasmus.mcp.servers import McpServers
from erasmus.mcp.client import StdioClient
from erasmus.utils.rich_console import print_table, get_console_logger, get_console
from erasmus.utils.paths import get_path_manager
from rich.syntax import Syntax
from rich.panel import Panel
# from erasmus.cli.github_mcp_commands import github_app # Commented out
import json # For JSON processing in tool responses
import click
from rich.table import Table
from datetime import datetime
import re

# Helper function to format GitHub commits in a readable way
def format_github_commits(commits_data):
    """Format GitHub commits data into a more readable format.
    
    Args:
        commits_data: The raw commits data from GitHub API
        
    Returns:
        A simplified list of commit information
    """
    try:
        # Try to parse the JSON if it's a string
        if isinstance(commits_data, str):
            try:
                commits_data = json.loads(commits_data)
            except json.JSONDecodeError:
                return commits_data
        
        # Handle different response formats
        if isinstance(commits_data, dict) and "result" in commits_data:
            commits_data = commits_data["result"]
        
        # Extract commits list if nested in another structure
        if isinstance(commits_data, dict) and "content" in commits_data:
            content = commits_data["content"]
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and "text" in content[0]:
                    try:
                        commits_data = json.loads(content[0]["text"])
                    except (json.JSONDecodeError, TypeError):
                        commits_data = content
        
        # Find the actual commits array
        if isinstance(commits_data, dict):
            for key in commits_data:
                if isinstance(commits_data[key], list) and len(commits_data[key]) > 0 and isinstance(commits_data[key][0], dict) and "sha" in commits_data[key][0]:
                    commits_data = commits_data[key]
                    break
        
        # Process the commits if we have a list
        if isinstance(commits_data, list):
            formatted_commits = []
            for commit in commits_data:
                if isinstance(commit, dict):
                    # Get commit details, handling nested structures
                    commit_info = {}
                    
                    # SHA
                    sha = commit.get("sha", "")
                    if sha:
                        commit_info["sha"] = sha[:8]  # Just first 8 chars
                    
                    # Author
                    commit_obj = commit.get("commit", {})
                    if isinstance(commit_obj, dict):
                        author_obj = commit_obj.get("author", {})
                        if isinstance(author_obj, dict) and "name" in author_obj:
                            commit_info["author"] = author_obj["name"]
                        
                        # Date
                        if isinstance(author_obj, dict) and "date" in author_obj:
                            commit_info["date"] = author_obj["date"]
                        
                        # Message
                        message = commit_obj.get("message", "")
                        if message:
                            # Get just the first line of the message
                            commit_info["message"] = message.split('\n')[0]
                    
                    # URL
                    url = commit.get("html_url", "")
                    if url:
                        commit_info["url"] = url
                    
                    formatted_commits.append(commit_info)
            return formatted_commits
    except Exception as e:
        logger.debug(f"Error formatting GitHub commits: {e}")
    
    # Return original data if anything fails
    return commits_data

mcp_registry = McpRegistry()
mcp_servers = McpServers()
mcp_client = StdioClient()
mcp_app = typer.Typer(help="Manage MCP servers and clients.")
path_manager = get_path_manager()
console = get_console()
logger = get_console_logger()

# New registry configuration management subcommand group
registry_config_app = typer.Typer(
    name="registry", 
    help="Manage MCP server configurations (mcp_config.json) and lifecycle (EXPERIMENTAL).",
    no_args_is_help=False  # Ensure our callback controls the no-args output
)
mcp_app.add_typer(registry_config_app, name="registry")

@registry_config_app.callback(invoke_without_command=True)
def registry_app_callback(ctx: typer.Context):
    """Display available registry subcommands if 'erasmus mcp registry' is called without a subcommand."""
    if ctx.invoked_subcommand is None:
        command_rows = [
            ["show", "Show the path to the mcp_config.json file being used."],
            ["edit", "Open mcp_config.json for editing using nano."],
            ["start", "(EXPERIMENTAL) Start a persistent MCP server process (placeholder)"],
            ["stop", "(EXPERIMENTAL) Stop a persistent MCP server process (placeholder)"],
        ]
        print_table(["Subcommand", "Description"], command_rows, title="Available Registry Subcommands")
        typer.echo("\nFor more information about a subcommand, run:")
        typer.echo("  erasmus mcp registry <subcommand> --help")
        raise typer.Exit(0)

@registry_config_app.command("show")
def registry_config_show():
    """Show the path to the mcp_config.json file being used."""
    config_path = mcp_servers.config_path
    logger.info(f"Displaying content of mcp_config.json from: {config_path}")
    console.print(f"MCP Configuration from: [cyan]{config_path}[/cyan]")

    if not config_path.exists():
        console.print(f"[yellow]Warning:[/yellow] MCP configuration file not found at {config_path}")
        return

    try:
        # Get the server data as a dictionary of McpServer Pydantic models
        servers_data_models = mcp_servers.get_servers()
        # Convert Pydantic models to dictionaries for JSON serialization
        servers_dict = {name: server.model_dump() for name, server in servers_data_models.items()}
        # Create the top-level structure expected in mcp_config.json
        config_to_display = {"mcpServers": servers_dict}
        
        json_str = json.dumps(config_to_display, indent=2)
        console.print(Syntax(json_str, "json", theme="native", line_numbers=True))
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] MCP configuration file not found at {config_path}")
    except json.JSONDecodeError:
        console.print(f"[red]Error:[/red] Could not decode JSON from {config_path}. File may be corrupted.")
    except Exception as error:
        console.print(f"[red]Error displaying MCP configuration:[/red] {error}")

@registry_config_app.command("edit")
def registry_config_edit():
    """Open mcp_config.json for editing using nano."""
    config_path = mcp_servers.config_path
    if not config_path.exists():
        logger.warning(f"mcp_config.json not found at {config_path}. You can create it by running this command.")
        console.print(f"[yellow]mcp_config.json not found at {config_path}.[/yellow]")
        # Optionally, ask to create or create a template?
        # For now, just open nano, which will create it if it doesn't exist.
    
    console.print(f"Opening [cyan]{config_path}[/cyan] with nano...")
    console.print(f"Close the editor to continue. If nano is not your preferred editor, please edit the file manually.")
    typer.run(["nano", str(config_path)]) # typer.run for external commands
    logger.info(f"nano editor closed for {config_path}.")
    console.print(f"Finished editing {config_path}.")
    console.print("Reloading MCPRegistry to reflect potential changes...")
    try:
        mcp_registry.load_registry() # Reload the main registry which depends on mcp_config.json via McpServers
        console.print("[green]MCPRegistry reloaded successfully.[/green]")
    except Exception as error:
        logger.error(f"Error reloading MCPRegistry after edit: {error}")
        console.print(f"[red]Error reloading MCPRegistry: {error}[/red]")

@registry_config_app.command("start")
@click.argument("name", type=str)
def start_server_lifecycle(name: str):
    """(EXPERIMENTAL) Start a persistent MCP server process (placeholder)."""
    # This is a placeholder for future SSE/persistent connection management
    logger.info(f"Attempting to start server (lifecycle): {name} (Placeholder)")
    console.print(f"[yellow]EXPERIMENTAL:[/yellow] Starting server '{name}'. This feature is a placeholder.")
    # Actual implementation would involve using McpServers to get server cmd and run it as a persistent process.
    # error.g., mcp_servers.start_server_process(name)
    console.print(f"TODO: Implement persistent start for server '{name}'.")

@registry_config_app.command("stop")
@click.argument("name", type=str)
def stop_server_lifecycle(name: str):
    """(EXPERIMENTAL) Stop a persistent MCP server process (placeholder)."""
    # This is a placeholder for future SSE/persistent connection management
    logger.info(f"Attempting to stop server (lifecycle): {name} (Placeholder)")
    console.print(f"[yellow]EXPERIMENTAL:[/yellow] Stopping server '{name}'. This feature is a placeholder.")
    # Actual implementation would involve managing the persistent process.
    # error.g., mcp_servers.stop_server_process(name)
    console.print(f"TODO: Implement persistent stop for server '{name}'.")


server_app = typer.Typer(help="Manage and interact with MCP servers and their tools via the new MCPRegistry.")
mcp_app.add_typer(server_app, name="servers")

@server_app.callback(invoke_without_command=True)
def servers_app_callback(ctx: typer.Context):
    """Display available servers if 'erasmus mcp servers' is called without a subcommand."""
    if ctx.invoked_subcommand is None:
        command_rows = [
            ["list", "List all available MCP servers from the registry"], # Changed to just 'list'
        ]
        
        # Dynamically add registered servers
        if mcp_registry and hasattr(mcp_registry, 'registry') and "mcp_servers" in mcp_registry.registry:
            for s_name, s_data in mcp_registry.registry["mcp_servers"].items():
                server_info = s_data.get("server", {})
                description = server_info.get("description", f"Access tools for the {s_name} server.") 
                command_rows.append([s_name, description]) # Changed to just s_name
        
        print_table(["Subcommand", "Description"], command_rows, title="Available Server Subcommands") # Updated column title
        typer.echo("\nFor more information about a subcommand, run:")
        typer.echo("  erasmus mcp servers <subcommand> --help") # Updated help text
        raise typer.Exit(0)



# --- Commands for `erasmus mcp servers ...` --- 

@server_app.command("list")
def list_mcp_servers():
    """List all available MCP servers based on the loaded MCPRegistry."""
    if not mcp_registry or not mcp_registry.registry or "mcp_servers" not in mcp_registry.registry:
        logger.warning("MCPRegistry not available or not populated. Cannot list servers.")
        console.print("[yellow]MCPRegistry is not populated. No servers to list.[/yellow]")
        console.print(f"Ensure '{mcp_servers.config_path}' is configured and `erasmus mcp registry load` (or similar) has run.")
        return

    server_list = list(mcp_registry.registry["mcp_servers"].keys())
    if not server_list:
        console.print("[yellow]No MCP servers found in the registry.[/yellow]")
        logger.info("No MCP servers found in mcp_registry.")
    else:
        logger.info(f"Available MCP servers: {server_list}")
        headers = ["Server Name"]
        rows = [(name,) for name in server_list]
        print_table(headers, rows, title="Available MCP Servers")


@mcp_app.callback(invoke_without_command=True)
def mcp_callback(ctx: typer.Context):
    """
    Manage MCP servers and clients.
    """
    if ctx.invoked_subcommand is None:
        command_rows = [
            ["servers", "Manage and interact with MCP servers and their tools"],
            ["registry", "Manage MCP server configurations (mcp_config.json) and lifecycle"],
        ]
        print_table(["Commands", "Description"], command_rows, title="Available MCP Subcommands")
        typer.echo("\nFor more information about a command, run:")
        typer.echo("  erasmus mcp <command> --help")
        raise typer.Exit(0)


# Dynamically add server subcommands using MCPRegistry
if mcp_registry and hasattr(mcp_registry, 'registry') and isinstance(mcp_registry.registry, dict) and "mcp_servers" in mcp_registry.registry:
    for server_name, server_data in mcp_registry.registry["mcp_servers"].items():
        help_text = f"Access {server_name} MCP server tools."
        # Attempt to get a more descriptive help message from the registry data
        # The structure in registry.json is registry['mcp_servers'][server_name]['server'] for server details
        # and registry['mcp_servers'][server_name]['tools'] for tool details.
        server_info = server_data.get("server", {})
        if isinstance(server_info, dict):
            annotations = server_info.get("annotations", {})
            if isinstance(annotations, dict) and "title" in annotations:
                help_text = annotations["title"]
            elif "description" in server_info: # Fallback to server description
                help_text = server_info["description"]
        
        server_description = server_data.get("server", {}).get("description", f"Tools for MCP Server: {server_name}")
        dynamic_server_typer = typer.Typer(help=f"MCP Server: {server_name} - {server_description}", no_args_is_help=False) # no_args_is_help=False to allow our callback

        # Dynamically add callback for individual server app (error.g., `erasmus mcp servers github`)
        def create_dynamic_server_app_callback(current_server_name: str, current_server_tools_data: dict):
            def dynamic_server_callback(ctx: typer.Context):
                if ctx.invoked_subcommand is None:
                    tool_rows = []
                    if not current_server_tools_data:
                        typer.echo(f"No tools explicitly registered for server '{current_server_name}' in the registry.")
                    else:
                        for tool_name, tool_data in current_server_tools_data.items():
                            tool_title = tool_data.get("annotations", {}).get("title", tool_name.replace("_", " ").title())
                            base_desc = tool_data.get("description", f"Execute {tool_name}")
                            full_description = f"{tool_title} - {base_desc}"

                            input_schema = tool_data.get('inputSchema', {})
                            properties = input_schema.get('properties', {})
                            
                            if properties:
                                param_details_str = "\n  Params:"
                                for param_name, param_info in properties.items():
                                    param_type = param_info.get('type', 'any')
                                    param_desc = param_info.get('description', 'No specific description.')
                                    # Check if the parameter is required
                                    is_required = param_name in input_schema.get('required', [])
                                    required_str = " (required)" if is_required else ""
                                    param_details_str += f"\n    - {param_name}{required_str} ({param_type}): {param_desc}"
                                full_description += param_details_str
                                
                            tool_rows.append([tool_name, full_description])
                    
                    if tool_rows:
                        print_table(["Tool Subcommand", "Description"], tool_rows, title=f"Available Tools for Server: {current_server_name}")
                    else:
                        typer.echo(f"No tools found or listed for server: {current_server_name}")
                    typer.echo("\nFor more information about a specific tool, run:")
                    typer.echo(f"  erasmus mcp servers {current_server_name} <tool_subcommand> --help")
                    raise typer.Exit(0)
            return dynamic_server_callback

        # Get the tools data for the current server to pass to the callback factory
        tools_for_current_server = server_data.get("tools", {})
        dynamic_server_typer.callback(invoke_without_command=True)(
            create_dynamic_server_app_callback(server_name, tools_for_current_server)
        )

        # Dynamically add tool commands for this server
        if isinstance(server_data, dict) and "tools" in server_data:
            for tool_name, tool_schema in server_data.get("tools", {}).items():
                try:
                    # 1. Create Pydantic model for tool's input schema
                    # Ensure mcp_registry has the _create_tool_model method accessible or replicate logic
                    # For now, assuming mcp_registry instance can be used if it's correctly initialized
                    # and its methods are suitable.
                    # We need an instance of MCPRegistry to call _create_tool_model.
                    # The mcp_registry global instance should work.
                    
                    # Guard against tool_schema not being a dict or missing inputSchema
                    if not isinstance(tool_schema, dict) or "inputSchema" not in tool_schema:
                        logger.warning(f"Skipping tool {tool_name} for server {server_name} due to missing or invalid schema.")
                        continue

                    # 2. Define the actual command function
                    def _create_dynamic_command_func_for_tool(s_name: str, tool_name: str, t_schema: dict):
                        """Helper to create the actual callable command function with correct signature."""
                        
                        input_schema = t_schema.get("inputSchema", {})
                        original_param_schema_types = {}
                        params_for_signature = []

                        # Add context parameter for Typer if needed by advanced features (rarely for simple commands)
                        # params_for_signature.append(inspect.Parameter("ctx", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=typer.Context))

                        for param_name, param_info in input_schema.get("properties", {}).items():
                            param_schema_type = param_info.get("type", "string")
                            original_param_schema_types[param_name] = param_schema_type
                            is_required = param_name in input_schema.get("required", [])
                            param_cli_help = param_info.get("description", f"Parameter '{param_name}' for {tool_name}")

                            if param_schema_type in ["object", "array"]:
                                typer_annotation = str | None if not is_required else str
                                param_cli_help += " (Input as JSON string)"
                            elif param_schema_type == "integer":
                                typer_annotation = int | None if not is_required else int
                            elif param_schema_type == "number":
                                typer_annotation = float | None if not is_required else float
                            elif param_schema_type == "boolean":
                                typer_annotation = bool # Typer makes bool | None a flag --name/--no-name
                            else:
                                typer_annotation = str | None if not is_required else str

                            cli_default_value = inspect.Parameter.empty
                            if not is_required:
                                schema_default = param_info.get("default")
                                if schema_default is not None:
                                    if param_schema_type in ["object", "array"]:
                                        try: cli_default_value = json.dumps(schema_default)
                                        except TypeError: 
                                            logger.warning(f"Could not JSON serialize default for {param_name} in {tool_name}. No default for CLI.")
                                            cli_default_value = None
                                    else:
                                        cli_default_value = schema_default
                                else:
                                    cli_default_value = None
                            
                            parameter_kind = inspect.Parameter.KEYWORD_ONLY
                            if is_required:
                                typer_option_itself = typer.Option(..., help=param_cli_help) 
                            else:
                                typer_option_itself = typer.Option(cli_default_value, help=param_cli_help)

                            params_for_signature.append(
                                inspect.Parameter(param_name, parameter_kind, default=typer_option_itself, annotation=typer_annotation)
                            )

                        def generated_command_function(**kwargs):
                            payload_for_client = {}
                            for name, value_from_cli in kwargs.items():
                                if value_from_cli is None and not (name in input_schema.get("required", []) or (input_schema.get("properties", {}).get(name, {}).get("default") is not None)):
                                    continue

                                original_type = original_param_schema_types.get(name)
                                if original_type in ["object", "array"] and isinstance(value_from_cli, str):
                                    try: payload_for_client[name] = json.loads(value_from_cli)
                                    except json.JSONDecodeError as e_json:
                                        rich_console.print(f"[red]Error: Invalid JSON for '{name}':[/red] {value_from_cli}")
                                        rich_console.print(f"[red]{e_json}[/red]")
                                        raise typer.Exit(code=1)
                                else:
                                    payload_for_client[name] = value_from_cli
                            
                            # The RPC method is always "tools/call"
                            # The parameters for "tools/call" include the tool's actual name and its specific arguments
                            actual_method_for_rpc = "tools/call"
                            structured_payload = {
                                **payload_for_client,  # Pass parameters directly at the top level
                                "name": tool_name  # tool_name is the actual tool name like "create_issue"
                            }
                            
                            rich_console = get_console() # Ensure we use get_console() for Rich features
                            with rich_console.status(f"Executing {tool_name} on {s_name}...", spinner="dots"):
                                try:
                                    if s_name == "github" and not os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
                                        rich_console.print("[bold red]Error: GITHUB_PERSONAL_ACCESS_TOKEN environment variable is not set.[/bold red]")
                                        rich_console.print("Please set it to use GitHub MCP tools.")
                                        raise typer.Exit(code=1)
                                    
                                    logger.debug(f"Sending to MCP client: Server='{s_name}', Method='{actual_method_for_rpc}', Payload='{structured_payload}'")
                                    stdout, stderr = mcp_client.communicate(s_name, actual_method_for_rpc, structured_payload)
                                    
                                    if stderr:
                                        logger.warning(f"MCP Server '{s_name}' stderr: {stderr.strip()}")
                                        # Potentially print non-critical stderr to console as well, if desired
                                        # console.print(f"[dim]Server messages: {stderr.strip()}[/dim]")
                                    if stdout:
                                        # Split stdout into lines and parse each as JSON if possible
                                        lines = [line for line in stdout.strip().splitlines() if line.strip()]
                                        responses = []
                                        for idx, line in enumerate(lines):
                                            try:
                                                parsed = json.loads(line)
                                                responses.append(parsed)
                                            except json.JSONDecodeError:
                                                responses.append(line)
                                        # Show all responses, but highlight the last (tool) response
                                        for i, resp in enumerate(responses):
                                            section_title = f"Server Response ({'Tool Call' if i == len(responses)-1 else 'Init'})"
                                            
                                            # Default to string representation
                                            display_object = str(resp)
                                            
                                            # Only process dictionaries
                                            if type(resp) == dict:
                                                # Start with the raw response
                                                content_to_display = resp
                                                
                                                # Try to extract nested content if available
                                                try:
                                                    if "result" in resp and type(resp["result"]) == dict:
                                                        result = resp["result"]
                                                        
                                                        # Check for nested content
                                                        if "content" in result and type(result["content"]) == list and len(result["content"]) > 0:
                                                            first_content = result["content"][0]
                                                            
                                                            if type(first_content) == dict and "text" in first_content and type(first_content["text"]) == str:
                                                                nested_text = first_content["text"]
                                                                
                                                                # Try to parse as JSON
                                                                try:
                                                                    parsed_json = json.loads(nested_text)
                                                                    content_to_display = parsed_json
                                                                except json.JSONDecodeError:
                                                                    # If not valid JSON, use as text
                                                                    content_to_display = nested_text
                                                        else:
                                                            # Use result directly if no content array
                                                            content_to_display = result
                                                except (TypeError, KeyError) as e:
                                                    # If any error occurs during extraction, log it and use original response
                                                    logger.debug(f"Error extracting nested content: {e}")
                                                    content_to_display = resp
                                                
                                                # Format as pretty JSON with proper indentation
                                                try:
                                                    # Special handling for GitHub commands
                                                    if s_name == "github":
                                                        # For list_commits, directly extract and format the commits
                                                        if tool_name == "list_commits":
                                                            # Try to find the commits in the response
                                                            if isinstance(resp, dict) and "result" in resp:
                                                                # Try to parse the content
                                                                result = resp["result"]
                                                                if isinstance(result, dict) and "content" in result and isinstance(result["content"], list):
                                                                    for content_item in result["content"]:
                                                                        if isinstance(content_item, dict) and "text" in content_item:
                                                                            try:
                                                                                # Try to parse the text as JSON
                                                                                commits_json = json.loads(content_item["text"])
                                                                                # Extract the actual commits array
                                                                                if isinstance(commits_json, dict):
                                                                                    for key in commits_json:
                                                                                        if isinstance(commits_json[key], list):
                                                                                            commits = commits_json[key]
                                                                                            # Format the commits
                                                                                            formatted_commits = []
                                                                                            for commit in commits:
                                                                                                if isinstance(commit, dict):
                                                                                                    commit_info = {
                                                                                                        "sha": commit.get("sha", "Unknown")[:8],
                                                                                                        "author": commit.get("commit", {}).get("author", {}).get("name", "Unknown"),
                                                                                                        "date": commit.get("commit", {}).get("author", {}).get("date", "Unknown"),
                                                                                                        "message": commit.get("commit", {}).get("message", "No message").split('\n')[0],
                                                                                                        "url": commit.get("html_url", "")
                                                                                                    }
                                                                                                    formatted_commits.append(commit_info)
                                                                                            content_to_display = formatted_commits
                                                                                            break
                                                                            except Exception as e:
                                                                                logger.debug(f"Error parsing commits JSON: {e}")
                                                    
                                                    # Extract the actual data from nested response if possible
                                                    if isinstance(content_to_display, dict) and "result" in content_to_display:
                                                        content_to_display = content_to_display["result"]
                                                    
                                                    # Use 4-space indentation for better readability
                                                    indented_json_string = json.dumps(content_to_display, indent=4, sort_keys=True)
                                                    display_object = Syntax(indented_json_string, "json", theme="monokai", line_numbers=True, word_wrap=True)
                                                except Exception as e:
                                                    logger.debug(f"Error formatting JSON: {e}")
                                                    display_object = str(content_to_display)
                                            
                                            # Display the response
                                            rich_console.print(Panel(display_object, title=section_title, border_style="blue", expand=False))
                                    else:
                                        rich_console.print(f"[yellow]No stdout content received from {tool_name}.[/yellow]")
                                except McpError as e_mcp:
                                    console.print(f"[red]McpError ({tool_name} on {s_name}): {e_mcp}[/red]")
                                    raise typer.Exit(code=1)
                                except Exception as e_exc:
                                    console.print(f"[red]Error ({tool_name} on {s_name}): {e_exc}[/red]")
                                    logger.exception(f"Error in {tool_name} on {s_name}")
                                    raise typer.Exit(code=1)
                        
                        # Correctly indented block, belongs to _create_dynamic_command_func_for_tool
                        generated_command_function.__signature__ = inspect.Signature(params_for_signature)
                        tool_description = t_schema.get("description", f"Execute {tool_name}.")
                        annotations_title = t_schema.get("annotations", {}).get("title")
                        generated_command_function.__doc__ = f"{annotations_title}\n{tool_description}" if annotations_title else tool_description
                        generated_command_function.__name__ = f"{s_name}_{tool_name}_cmd"
                        return generated_command_function

                    # 3. Create and register the command
                    tool_title = tool_schema.get("annotations", {}).get("title", tool_name.replace("_", " ").title())
                    cmd_fn = _create_dynamic_command_func_for_tool(server_name, tool_name, tool_schema)
                    
                    dynamic_server_typer.command(name=tool_name, help=tool_title)(cmd_fn)
                    # logger.debug(f"  Dynamically added tool command: {tool_name} to {server_name}")

                except Exception as error:
                    logger.error(f"Failed to create command for tool {tool_name} on server {server_name}: {error}")
                    # Optionally, re-raise or continue to next tool
                    
        server_app.add_typer(dynamic_server_typer, name=server_name)
        # logger.debug(f"Dynamically added MCP server command group: {server_name} using MCPRegistry")

else:
    logger.warning("MCPRegistry not available or not populated correctly. No dynamic server commands will be added.")

if __name__ == "__main__":
    try:
        mcp_app()
    except Exception as error:
        print_table(["Error"], [[str(error)]], title="CLI Error")
        raise typer.Exit(1)

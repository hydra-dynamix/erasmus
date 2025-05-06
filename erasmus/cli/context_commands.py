# """
# CLI commands for managing development contexts.
# """

# import typer
# from loguru import logger
# from erasmus.context import ContextManager, ContextError
# import xml.dom.minidom as minidom
# from erasmus.utils.rich_console import print_table, get_console
# import os
# from rich.panel import Panel
# import xml.etree.ElementTree as ET
# from erasmus.utils.paths import get_path_manager

# context_manager = ContextManager()
# console = get_console()
# context_app = typer.Typer(help="Manage development contexts and their files.")


# @context_app.command("get")
# def get_context(name: str = typer.Argument(..., help="Name of the context to get")):
#     """Get detailed information of a development context."""
#     try:
#         # Use display_context to print full details
#         context_manager.display_context(name)
#     except ContextError as error:
#         # Extract underlying error if prefixed by display_context
#         error_msg = str(e)
#         prefix = "Failed to display context: "
#         if error_msg.startswith(prefix):
#             error_msg = error_msg[len(prefix) :]
#         typer.echo(f"Error: Failed to get context: {error_msg}")
#         raise typer.Exit(1)
#     # Successful display
#     raise typer.Exit(0)


# def show_context_help_and_exit():
#     """Show help menu and exit with error code."""
#     command_rows = [
#         ["erasmus context list", "List all contexts"],
#         ["erasmus context create", "Create a new context"],
#         ["erasmus context show", "Show context details"],
#         ["erasmus context update", "Update context files"],
#         ["erasmus context edit", "Edit context files"],
#         ["erasmus context store", "Store the current context"],
#         ["erasmus context select", "Select and load a context interactively"],
#         ["erasmus context load", "Load a context by name to root .ctx XML files"],
#     ]
#     print_table(["Command", "Description"], command_rows, title="Available Commands")
#     typer.echo("\nFor more information about a command, run:")
#     typer.echo("  erasmus context <command> --help")
#     raise typer.Exit(1)


# @context_app.callback(invoke_without_command=True)
# def context_callback(ctx: typer.Context):
#     """
#     Manage development contexts and their files.
#     """
#     if ctx.invoked_subcommand is None:
#         command_rows = [
#             ["erasmus context list", "List all contexts"],
#             ["erasmus context create", "Create a new context"],
#             ["erasmus context show", "Show context details"],
#             ["erasmus context update", "Update context files"],
#             ["erasmus context edit", "Edit context files"],
#             ["erasmus context store", "Store the current context"],
#             ["erasmus context select", "Select and load a context interactively"],
#             ["erasmus context load", "Load a context by name to root .ctx XML files"],
#         ]
#         print_table(["Command", "Description"], command_rows, title="Available Commands")
#         typer.echo("\nFor more information about a command, run:")
#         typer.echo("  erasmus context <command> --help")
#         raise typer.Exit(0)


# @context_app.command()
# def create(name: str = typer.Argument(None, help="Name of the context to create")):
#     """Create a new development context and display its path."""
#     try:
#         if not name:
#             name = typer.prompt("Enter the context name")
#         if not name:
#             print_table(
#                 ["Error"],
#                 [["Context name is required."]],
#                 title="Context Creation Failed",
#             )
#             raise typer.Exit(1)
#         context_path = context_manager.get_context_path(name)
#         context_manager.create_context(name)
#         # Retrieve created context model for path
#         context = context_manager.get_context(name)
#         # Display created context in a table
#         context_rows = [[context_path]]
#         print_table(["Context Path"], context_rows, title=f"Created Context: {name}")
#         raise typer.Exit(0)
#     except ContextError as error:
#         print_table(["Error"], [[str(error)]], title="Context Creation Failed")
#         raise typer.Exit(1)


# @context_app.command()
# def delete(name: str = typer.Argument(None, help="Name of the context to delete")):
#     """Delete a context.

#     This command permanently removes a context folder and its files.
#     Use with caution as this action cannot be undone.
#     """
#     try:
#         if not name:
#             contexts = context_manager.list_contexts()
#             if not contexts:
#                 print_table(["Info"], [["No contexts found"]], title="Available Contexts")
#                 raise typer.Exit(1)
#             context_rows = [
#                 [str(index + 1), context_name] for index, context_name in enumerate(contexts)
#             ]
#             print_table(["#", "Context Name"], context_rows, title="Available Contexts")
#             choice = typer.prompt("Select a context by number or name")
#             selected = None
#             if choice.isdigit():
#                 index = int(choice)
#                 if 1 <= index <= len(contexts):
#                     selected = contexts[index - 1]
#             else:
#                 if choice in contexts:
#                     selected = choice
#             if not selected:
#                 print_table(
#                     ["Error"],
#                     [[f"Invalid selection: {choice}"]],
#                     title="Context Deletion Failed",
#                 )
#                 raise typer.Exit(1)
#             name = selected
#         context_manager.delete_context(name)
#         print_table(["Info"], [[f"Deleted context: {name}"]], title="Context Deleted")
#         raise typer.Exit(0)
#     except Exception as error:
#         print_table(["Error"], [[str(e)]], title="Context Deletion Failed")
#         raise typer.Exit(1)


# @context_app.command()
# def list():
#     """List all development contexts.

#     This command shows all available contexts and their basic information.
#     Use 'show' to view detailed information about a specific context.
#     """
#     try:
#         contexts = context_manager.list_contexts()
#         if not contexts:
#             print_table(["Info"], [["No contexts found"]], title="Available Contexts")
#             return

#         # Display contexts in a table
#         context_rows = [[context] for context in contexts]
#         print_table(["Context Name"], context_rows, title="Available Contexts")
#     except ContextError as error:
#         print_table(["Error"], [[str(error)]], title="Context Listing Failed")
#         show_context_help_and_exit()


# def preview(text, lines=10):
#     if not text:
#         return ""
#     split = text.splitlines()
#     if len(split) > lines:
#         return "\n".join(split[:lines]) + "\n..."
#     return text


# @context_app.command()
# def show(name: str = typer.Argument(None, help="Name of the context to show")):
#     """Show details of a development context.

#     This command displays detailed information about a specific context,
#     including file sizes and paths. If no name is supplied, it will prompt the user to select one.
#     """
#     try:
#         if not name:
#             # List available contexts and prompt for selection
#             contexts = context_manager.list_contexts()
#             if not contexts:
#                 print_table(["Info"], [["No contexts found"]], title="Available Contexts")
#                 raise typer.Exit(1)
#             context_rows = [
#                 [str(index + 1), context_name] for index, context_name in enumerate(contexts)
#             ]
#             print_table(["#", "Context Name"], context_rows, title="Available Contexts")
#             choice = typer.prompt("Select a context by number or name")
#             selected = None
#             if choice.isdigit():
#                 index = int(choice)
#                 if 1 <= index <= len(contexts):
#                     selected = contexts[index - 1]
#             else:
#                 if choice in contexts:
#                     selected = choice
#             if not selected:
#                 print_table(
#                     ["Error"],
#                     [[f"Invalid selection: {choice}"]],
#                     title="Context Show Failed",
#                 )
#                 raise typer.Exit(1)
#             name = selected
#         context_dir = context_manager.get_context_path(name)

#         def read_context_file(context_dir, file_type):
#             for ext in (".md", ".md"):
#                 file_path = context_dir / f"ctx.{file_type}{ext}"
#                 if file_path.exists():
#                     return file_path.read_text()
#             return ""

#         context_rows = [
#             ["Path", str(context_dir)],
#             ["Architecture", preview(read_context_file(context_dir, "architecture"))],
#             ["Progress", preview(read_context_file(context_dir, "progress"))],
#             ["Tasks", preview(read_context_file(context_dir, "tasks"))],
#             ["Protocol", preview(read_context_file(context_dir, "protocol"))],
#         ]
#         print_table(
#             ["Field", "Preview (first 10 lines)"],
#             context_rows,
#             title=f"Context: {name}",
#         )
#     except ContextError as error:
#         print_table(["Error"], [[str(error)]], title="Context Show Failed")
#         show_context_help_and_exit()


# @context_app.command()
# def update(
#     name: str = typer.Argument(None, help="Name of the context to update"),
#     file_type: str = typer.Argument(
#         None, help="Type of file to update (architecture, progress, tasks, protocol)"
#     ),
#     content: str = typer.Argument(None, help="Content to write to the file"),
# ):
#     """Update a file in a development context.

#     This command updates the content of a specific file in a context.
#     The file type must be one of: architecture, progress, tasks, or protocol.
#     """
#     try:
#         if not name:
#             # List available contexts and prompt for selection
#             contexts = context_manager.list_contexts()
#             if not contexts:
#                 print_table(["Info"], [["No contexts found"]], title="Available Contexts")
#                 raise typer.Exit(1)
#             context_rows = [
#                 [str(index + 1), context_name] for index, context_name in enumerate(contexts)
#             ]
#             print_table(["#", "Context Name"], context_rows, title="Available Contexts")
#             choice = typer.prompt("Select a context by number or name")
#             selected = None
#             if choice.isdigit():
#                 index = int(choice)
#                 if 1 <= index <= len(contexts):
#                     selected = contexts[index - 1]
#             else:
#                 if choice in contexts:
#                     selected = choice
#             if not selected:
#                 print_table(
#                     ["Error"],
#                     [[f"Invalid selection: {choice}"]],
#                     title="Context Update Failed",
#                 )
#                 raise typer.Exit(1)
#             name = selected
#         if not file_type:
#             file_type = typer.prompt(
#                 "Enter the file type to update (architecture, progress, tasks, protocol)"
#             )
#         if not file_type:
#             print_table(
#                 ["Error"],
#                 [["File type is required for update."]],
#                 title="Context Update Failed",
#             )
#             raise typer.Exit(1)
#         if content is None:
#             content = typer.prompt(f"Enter the new content for {file_type}")
#         if not content:
#             print_table(
#                 ["Error"],
#                 [["Content is required for update."]],
#                 title="Context Update Failed",
#             )
#             raise typer.Exit(1)
#         context_manager.update_file(name, file_type, content)
#         print_table(
#             ["Info"],
#             [[f"Updated {file_type} in context: {name}"]],
#             title="Context Updated",
#         )
#         raise typer.Exit(0)
#     except ContextError as error:
#         print_table(["Error"], [[str(error)]], title="Context Update Failed")
#         show_context_help_and_exit()


# @context_app.command()
# def cat(
#     name: str = typer.Argument(..., help="Name of the context"),
#     file_type: str = typer.Argument(
#         ..., help="Type of file to read (architecture, progress, tasks, protocol)"
#     ),
# ):
#     """Display the contents of a file in a development context.

#     This command shows the raw contents of a specific file in a context.
#     The file type must be one of: architecture, progress, tasks, or protocol.
#     """
#     try:
#         content = context_manager.read_file(name, file_type)
#         if content is None:
#             print_table(
#                 ["Error"],
#                 [[f"File not found: {file_type}"]],
#                 title="Context Cat Failed",
#             )
#             logger.info("Available file types: architecture, progress, tasks, protocol")
#             show_context_help_and_exit()

#         # Pretty print XML for better readability
#         try:
#             # Parse the XML content
#             dom = minidom.parseString(content)
#             # Pretty print with indentation
#             pretty_xml = dom.toprettyxml(indent="  ")
#             print(pretty_xml)
#         except Exception:
#             # If XML parsing fails, print the raw content
#             print(content)
#     except ContextError as error:
#         print_table(["Error"], [[str(error)]], title="Context Cat Failed")
#         show_context_help_and_exit()


# @context_app.command()
# def edit(
#     name: str = typer.Argument(None, help="Name of the context"),
#     file_type: str = typer.Argument(
#         None, help="Type of file to edit (architecture, progress, tasks, protocol)"
#     ),
#     editor: str = typer.Argument(None, help="Editor to use for editing"),
# ):
#     """Edit a file in a development context.

#     This command opens a file in your default editor (or specified editor).
#     The file type must be one of: architecture, progress, tasks, or protocol.
#     """
#     if not name:
#         # List available contexts and prompt for selection
#         contexts = context_manager.list_contexts()
#         if not contexts:
#             print_table(["Info"], [["No contexts found"]], title="Available Contexts")
#             raise typer.Exit(1)
#         context_rows = [
#             [str(index + 1), context_name] for index, context_name in enumerate(contexts)
#         ]
#         print_table(["#", "Context Name"], context_rows, title="Available Contexts")
#         choice = typer.prompt("Select a context by number or name")
#         selected = None
#         if choice.isdigit():
#             index = int(choice)
#             if 1 <= index <= len(contexts):
#                 selected = contexts[index - 1]
#         else:
#             if choice in contexts:
#                 selected = choice
#         if not selected:
#             print_table(
#                 ["Error"],
#                 [[f"Invalid selection: {choice}"]],
#                 title="Context Edit Failed",
#             )
#             raise typer.Exit(1)
#         name = selected
#     if not file_type:
#         file_type = typer.prompt(
#             "Enter the file type to edit (architecture, progress, tasks, protocol)"
#         )
#     if not file_type:
#         print_table(
#             ["Error"],
#             [["File type is required for edit."]],
#             title="Context Edit Failed",
#         )
#         raise typer.Exit(1)
#     context_dir = context_manager.get_context_path(name)
#     file_path = None
#     for ext in (".md", ".md"):
#         candidate = context_dir / f"ctx.{file_type}{ext}"
#         if candidate.exists():
#             file_path = candidate
#             break
#     if not file_path:
#         print_table(
#             ["Error"],
#             [[f"File does not exist: {file_type}"]],
#             title="Context Edit Failed",
#         )
#         raise typer.Exit(1)
#     editor_cmd = editor or os.environ.get("EDITOR", "nano")
#     os.system(f"{editor_cmd} {file_path}")
#     print_table(
#         ["Info"],
#         [[f"Edited {file_type} in context: {name}"]],
#         title="Context Edited",
#     )
#     raise typer.Exit(0)


# def get_title_from_architecture() -> str | None:
#     """Parse the title from the architecture file.

#     Returns:
#         The title if found, None otherwise.
#     """
#     try:
#         arch_file = context_manager.pm.get_architecture_file()
#         if not arch_file.exists():
#             return None

#         tree = ET.parse(arch_file)
#         root = tree.getroot()

#         # Try different possible paths to title
#         title_paths = [
#             ".//Title",  # Direct title tag
#             ".//Architecture/Title",  # Under Architecture
#             ".//Overview/Title",  # Under Overview
#             ".//Architecture/Overview/Title",  # Full path
#         ]

#         for path in title_paths:
#             title_elem = root.find(path)
#             if title_elem is not None and title_elem.text:
#                 return title_elem.text.strip()

#         return None
#     except Exception:
#         return None


# @context_app.command()
# def store(name: str = typer.Argument(None, help="Optional name to store the context under")):
#     """Store the current context. If no name is provided, uses the title from architecture file or prompts for one."""
#     try:
#         # If name not provided, try to get from architecture
#         if not name:
#             name = get_title_from_architecture()

#         # If still no name, prompt user
#         if not name:
#             name = typer.prompt("Enter a name for the context")

#         if not name:
#             console.print(
#                 Panel("Error: Context name is required", title="Context Store Failed", style="red")
#             )
#             show_context_help_and_exit()
#             raise typer.Exit(1)

#         context_manager.store_context(name)
#         console.print(
#             Panel(f"Context stored successfully as '{name}'", title="Context Store", style="green")
#         )
#     except Exception as error:
#         console.print(Panel(f"Error\n{str(e)}", title="Context Store Failed", style="red"))
#         show_context_help_and_exit()
#         raise typer.Exit(1)


# @context_app.command("load")
# def load_context(name: str = typer.Argument(None, help="Name of the context to load")):
#     """Load a stored context by name into the root .ctx XML files.

#     If no name is supplied, you will be prompted to select one interactively.
#     """
#     try:
#         if not name:
#             # List available contexts and prompt for selection
#             contexts = context_manager.list_contexts()
#             if not contexts:
#                 print_table(["Info"], [["No contexts found"]], title="Available Contexts")
#                 raise typer.Exit(1)
#             context_rows = [
#                 [str(index + 1), context_name] for index, context_name in enumerate(contexts)
#             ]
#             print_table(["#", "Context Name"], context_rows, title="Available Contexts")
#             choice = typer.prompt("Select a context by number or name")
#             selected = None
#             if choice.isdigit():
#                 index = int(choice)
#                 if 1 <= index <= len(contexts):
#                     selected = contexts[index - 1]
#             else:
#                 if choice in contexts:
#                     selected = choice
#             if not selected:
#                 print_table(
#                     ["Error"],
#                     [[f"Invalid selection: {choice}"]],
#                     title="Context Load Failed",
#                 )
#                 raise typer.Exit(1)
#             name = selected
#         context_manager.load_context(name)
#         print_table(["Info"], [[f"Loaded context: {name}"]], title="Context Loaded")
#         raise typer.Exit(0)
#     except ContextError as error:
#         print_table(["Error"], [[str(error)]], title="Context Load Failed")
#         raise typer.Exit(1)


# @context_app.command("select")
# def select_context():
#     """Interactively select a context and load its XML files."""
#     base_dir = context_manager.base_path
#     # Gather available contexts
#     try:
#         contexts = sorted(
#             [
#                 context_directory.name
#                 for context_directory in base_dir.iterdir()
#                 if context_directory.is_dir()
#             ]
#         )
#     except Exception as exception:
#         typer.echo(f"Error: Unable to list contexts: {exception}")
#         raise typer.Exit(1)
#     if not contexts:
#         typer.echo("No contexts found to select.")
#         raise typer.Exit(1)
#     # Display contexts in a table with create new option
#     context_rows = [["0", "Create New Context"]] + [
#         [str(index + 1), context_name] for index, context_name in enumerate(contexts)
#     ]
#     print_table(["#", "Context Name"], context_rows, title="Available Contexts")
#     choice = typer.prompt("Select a context by number or name (0 to create new)")
#     # Handle create new option
#     if choice == "0":
#         new_name = typer.prompt("Enter name for new context")
#         if not new_name:
#             typer.echo("Error: Context name is required")
#             raise typer.Exit(1)
#         try:
#             context_manager.create_context(new_name)
#             selected = new_name
#         except ContextError as error:
#             typer.echo(f"Error creating context: {error}")
#             raise typer.Exit(1)
#     else:
#         # Determine selected context name
#         selected = None
#         if choice.isdigit():
#             index = int(choice)
#             if 1 <= index <= len(contexts):
#                 selected = contexts[index - 1]
#         else:
#             if choice in contexts:
#                 selected = choice
#         if not selected:
#             typer.echo(f"Error: Invalid selection: {choice}")
#             raise typer.Exit(1)
#     # Load the selected context
#     try:
#         context_manager.load_context(selected)
#         typer.echo(f"Loaded context: {selected}")
#         raise typer.Exit(0)
#     except ContextError as exception:
#         typer.echo(f"Error: Failed to load context: {exception}")
#         raise typer.Exit(1)


# def setup_callback(ctx: typer.Context):
#     """Initialize the context manager and create initial context."""
#     try:
#         # Get path manager
#         path_manager = get_path_manager()

#         # Create erasmus directories
#         erasmus_dir = path_manager.erasmus_dir
#         context_dir = path_manager.context_dir
#         protocol_dir = path_manager.protocol_dir
#         template_dir = path_manager.template_dir

#         erasmus_dir.mkdir(parents=True, exist_ok=True)
#         context_dir.mkdir(parents=True, exist_ok=True)
#         protocol_dir.mkdir(parents=True, exist_ok=True)
#         template_dir.mkdir(parents=True, exist_ok=True)

#         print_table(["Info"], [[f"Erasmus folders created in: {erasmus_dir}"]], title="Setup")

#         # Create a template context in the context folder and update root .ctx.*.md
#         context_manager = ContextManager(base_path=str(context_dir))
#         project_name = path_manager.root_dir.name
#         context_manager.create_context(project_name)
#         print_table(["Info"], [[f"Template context created: {project_name}"]], title="Setup")

#         # Load the new context to root .ctx.*.md files
#         context_manager.load_context(project_name)
#         print_table(["Info"], [[f"Context loaded: {project_name}"]], title="Setup")

#     except Exception as error:
#         print_table(["Error"], [[str(e)]], title="Setup Failed")
#         raise typer.Exit(1)

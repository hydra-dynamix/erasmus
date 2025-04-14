# Target Functionality from watcher.py

## Core Functionality

### Project Setup and Management

- `setup_project()`: Initializes project with necessary files and directories
- `update_context(context)`: Updates the cursor rules file with current context
- `update_specific_file(file_type, content)`: Updates a specific file with given content
- `save_rules(context_content)`: Saves rules content to appropriate files based on IDE environment

### File Operations

- `safe_read_file(file_path)`: Safely reads a file with proper error handling
- `safe_write_file(file_path, content)`: Safely writes to a file with proper error handling
- `ensure_file_exists(file_path)`: Ensures file and its parent directories exist
- `get_rules_file_path()`: Gets the appropriate paths for rules files based on IDE environment
- `save_global_rules(rules_content)`: Saves global rules to appropriate location
- `save_context_rules(context_content)`: Saves context-specific rules to appropriate location

### Git Operations

- `GitManager` class: Lightweight Git repository management
  - `__init__(repo_path)`: Initializes with repository path
  - `_is_git_repo()`: Checks if path is a git repository
  - `_init_git_repo()`: Initializes a new git repository
  - `_run_git_command(command)`: Runs a git command and returns stdout and stderr
  - `stage_all_changes()`: Stages all changes in the repository
  - `commit_changes(message)`: Commits staged changes with given message
  - `validate_commit_message(message)`: Validates a commit message against conventions
  - `get_repository_state()`: Gets the current state of the repository
  - `get_current_branch()`: Gets the name of the current branch
- `determine_commit_type(diff_output)`: Programmatically determines appropriate commit type
- `extract_commit_message(response)`: Extracts commit message from AI response
- `make_atomic_commit()`: Makes an atomic commit with AI-generated commit message
- `check_creds()`: Checks OpenAI credentials

### File Watching

- `BaseWatcher` class: Base file watcher that accepts file paths and a callback
  - `__init__(file_paths, callback)`: Initializes with file paths and callback
  - `on_modified(event)`: Handles file modification events
- `MarkdownWatcher` class: Monitors markdown/setup files
  - `__init__()`: Initializes with file mapping from SETUP_FILES
  - `markdown_callback(file_key)`: Handles markdown file updates
- `ScriptWatcher` class: Monitors script file for changes
  - `__init__(script_path)`: Initializes with script path
  - `script_callback(file_key)`: Handles script file updates
- `run_observer(observer)`: Helper to run an observer in a thread

### Task Management

- `manage_task(action, **kwargs)`: Manages tasks in the context
  - Actions: 'add', 'update', 'note', 'list', 'get'
- `read_context_file()`: Reads the context file
- `write_context_file(context)`: Writes the context file
- `update_file_content(context, key, file_path)`: Updates context with file content
- `extract_project_name(content)`: Extracts project name from architecture content

### Program Control

- `restart_program()`: Restarts the current program
- `main()`: Main function to handle arguments and execute appropriate actions

## Command Line Interface

The script supports various command line arguments:

- `--setup`: Sets up the project
- `--update`: Updates a specific file
- `--watch`: Watches project files for changes
- `--task-action`: Manages tasks (add, update, note, list, get)
- `--git-action`: Manages git operations (status, branch, commit, push, pull)

## Dependencies

- OpenAI API for commit message generation
- Git for version control
- File system operations for file watching and management
- JSON for context storage
- Logging for error and information reporting

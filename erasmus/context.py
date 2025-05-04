#!/usr/bin/env python3
"""
Simplified Context CLI for Erasmus Development Workflow with Rich Console UI.
Provides commands to list, create, edit, store, select, and load contexts using centralized path management.
"""
import re
import shutil
import subprocess
from pathlib import Path
import typer
from typing import Optional, List, Dict

from erasmus.utils.paths import get_path_manager, IDE
from erasmus.utils.rich_console import get_console, get_console_logger, print_table, print_panel

context_app = typer.Typer(
    help='Context management CLI for Erasmus',
    no_args_is_help=True,
    rich_markup_mode='rich'
)
console = get_console()

logger = get_console_logger()
# central path manager
path_manager = get_path_manager()

ide_env = path_manager.ide


def ensure_dir(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def display_available_contexts(contexts: List[str], title: str = 'Available Contexts') -> None:
    """Display available contexts in a rich table format."""
    if not contexts:
        print_table(['Info'], [['No contexts found']], title=title)
        return

    context_rows = [[str(i + 1), name] for i, name in enumerate(contexts)]
    print_table(['#', 'Context Name'], context_rows, title=title)


def select_context_interactive(contexts: List[str]) -> Optional[str]:
    """Interactively select a context from a list."""
    if not contexts:
        logger.warning('No contexts available. Would you like to create a new context?')
        create_new = typer.confirm('Create a new context?', default=True)
        if create_new:
            new_context_name = typer.prompt('Enter a name for the new context')
            # TODO: Implement actual context creation logic
            logger.info(f'New context "{new_context_name}" created')
            return new_context_name
        return None

    display_available_contexts(contexts)
    while True:
        choice = typer.prompt('Select a context by number or name')
        
        # Try to match by number
        try:
            index = int(choice) - 1
            if 0 <= index < len(contexts):
                return contexts[index]
        except ValueError:
            pass
        
        # Try to match by name
        if choice in contexts:
            return choice
        
        logger.warning(f'Invalid selection: {choice}. Please try again.')
    
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(contexts):
                return contexts[index - 1]
        elif choice in contexts:
            return choice
        
        logger.error(f'Invalid selection: {choice}')
        return None


@context_app.command('list')
def list_contexts() -> None:
    """List all contexts for this project."""
    root = path_manager.get_context_dir()
    if not root.exists():
        logger.error('No contexts found.')
        raise typer.Exit(1)
    
    contexts = [d.name for d in sorted(root.iterdir()) if d.is_dir()]
    
    # If using Warp, also show rules from the database
    if path_manager.ide == IDE.warp:
        warp_rules = path_manager.get_warp_rules()
        if warp_rules:
            print_panel("Warp Rules Found", title="Warp Integration", style="blue")
            rules_rows = [[rule[0], rule[1]] for rule in warp_rules]
            print_table(['Type', 'ID'], rules_rows, title="Warp Rules")
    
    display_available_contexts(contexts)


@context_app.command('create')
def create_context(name: Optional[str] = None) -> None:
    """Create a new context using the architecture template."""
    if not name:
        name = typer.prompt('Context name')
    
    if not name:
        logger.error('Context name is required')
        raise typer.Exit(1)

    try:
        ctx_dir = path_manager.get_context_dir() / name
        ensure_dir(ctx_dir)
        
        # Create each context file with proper title
        ctx_files = [
            ('.ctx.architecture.md', path_manager.architecture_template),
            ('.ctx.tasks.md', path_manager.tasks_template),
            ('.ctx.progress.md', path_manager.progress_template)
        ]
        
        for filename, template_path in ctx_files:
            file_path = ctx_dir / filename
            if template_path.exists():
                content = template_path.read_text()
                # Replace title in template
                content = re.sub(r'<Title>.*?</Title>', f'<Title>{name}</Title>', content)
                content = re.sub(r'^# [^\n]*', f'# {name}', content)
            else:
                # Default content with title if template doesn't exist
                file_type = filename.split('.')[-2]
                content = f'# {name} {file_type.capitalize()}\n\n'
            file_path.write_text(content)
        
        # If using Warp, also create an entry in the database
        if path_manager.ide == IDE.warp:
            success = path_manager.update_warp_rules(
                document_type='CONTEXT',
                document_id=name,
                rule=content
            )
            if success:
                logger.success(f'Created context \'{name}\' in both filesystem and Warp database')
            else:
                logger.warning(f'Created context \'{name}\' in filesystem but failed to update Warp database')
        else:
            logger.success(f'Created context \'{name}\' at {ctx_dir}')
    
    except Exception as e:
        logger.error(f'Failed to create context: {str(e)}')
        raise typer.Exit(1)


@context_app.command('edit')
def edit_context(name: Optional[str] = None) -> None:
    """Open context file in default editor."""
    if not name:
        contexts = [d.name for d in sorted(path_manager.get_context_dir().iterdir()) if d.is_dir()]
        name = select_context_interactive(contexts)
        if not name:
            raise typer.Exit(1)

    file_path = path_manager.get_context_dir() / name / '.ctx.architecture.md'
    if not file_path.exists():
        logger.error(f'Context \'{name}\' not found.')
        raise typer.Exit(1)
    
    editor = subprocess.getoutput('which nano')  # Fallback to nano
    subprocess.run([editor, str(file_path)])
    
    # If using Warp, update the database after editing
    if path_manager.ide == IDE.warp:
        content = file_path.read_text()
        success = path_manager.update_warp_rules(
            document_type='CONTEXT',
            document_id=name,
            rule=content
        )
        if success:
            logger.success(f'Updated context \'{name}\' in both filesystem and Warp database')
        else:
            logger.warning(f'Updated context \'{name}\' in filesystem but failed to update Warp database')
    else:
        logger.success(f'Finished editing context \'{name}\'')


@context_app.command('store')
def store_context(name: Optional[str] = None) -> None:
    """Store current .ctx.* files as a new context."""
    arch = path_manager.get_architecture_file()
    if not name and arch.exists():
        text = arch.read_text()
        markdown = re.search(r'^#\s*Title:\s*(.+)$', text, re.MULTILINE)
        name = markdown.group(1).strip() if markdown else None

    if not name:
        name = typer.prompt('Context name')

    if not name:
        logger.error('Context name is required')
        raise typer.Exit(1)

    try:
        root = path_manager.get_context_dir()
        ctx_dir = root / name
        ensure_dir(ctx_dir)
        
        for f in (
            path_manager.get_architecture_file(),
            path_manager.get_progress_file(),
            path_manager.get_tasks_file(),
        ):
            if f.exists():
                shutil.copy2(f, ctx_dir / f.name)
        
        # If using Warp, store in the database as well
        if path_manager.ide == IDE.warp:
            arch_content = path_manager.get_architecture_file().read_text()
            success = path_manager.update_warp_rules(
                document_type='CONTEXT',
                document_id=name,
                rule=arch_content
            )
            if success:
                logger.success(f'Stored context \'{name}\' in both filesystem and Warp database')
            else:
                logger.warning(f'Stored context \'{name}\' in filesystem but failed to update Warp database')
        else:
            logger.success(f'Stored context \'{name}\'')
    
    except Exception as e:
        logger.error(f'Failed to store context: {str(e)}')
        raise typer.Exit(1)


@context_app.command('select')
def select_context() -> None:
    """Select and load a stored context."""
    root = path_manager.get_context_dir()
    contexts = [d.name for d in sorted(root.iterdir()) if d.is_dir()]
    
    # If using Warp, show database contexts as well
    if path_manager.ide == IDE.warp:
        warp_rules = path_manager.get_warp_rules()
        if warp_rules:
            warp_contexts = [rule[1] for rule in warp_rules if rule[0] == 'CONTEXT']
            contexts.extend([c for c in warp_contexts if c not in contexts])
    
    name = select_context_interactive(contexts)
    if not name:
        raise typer.Exit(1)

    try:
        load_context(name)
        logger.success(f'Selected and loaded context: {name}')
    except Exception as e:
        logger.error(f'Failed to select context: {str(e)}')
        raise typer.Exit(1)


@context_app.command('load')
def load_context(name: str) -> None:
    """Load stored context files into current directory."""
    ctx_dir = path_manager.get_context_dir() / name
    
    try:
        if ctx_dir.exists():
            for f in ctx_dir.glob('*.md'):
                dest = Path.cwd() / f.name
                shutil.copy2(f, dest)
            logger.success(f'Loaded context "{name}" from filesystem')
        elif path_manager.ide == IDE.warp:
            # Try loading from Warp database
            warp_rules = path_manager.get_warp_rules()
            if warp_rules:
                context_rule = next(
                    (rule for rule in warp_rules if rule[0] == 'CONTEXT' and rule[1] == name),
                    None
                )
                if context_rule:
                    dest = Path.cwd() / '.ctx.architecture.md'
                    dest.write_text(context_rule[2])
                    logger.success(f'Loaded context "{name}" from Warp database')
                else:
                    logger.error(f'Context "{name}" not found.')
                    raise typer.Exit(1)
        
        # Call update method to synchronize context
        from erasmus.file_monitor import _merge_rules_file
        _merge_rules_file()
        
    except Exception as e:
        logger.error(f'Failed to load context: {str(e)}')
        raise typer.Exit(1)


if __name__ == '__main__':
    context_app()

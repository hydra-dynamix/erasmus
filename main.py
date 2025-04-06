from pathlib import Path
from src.script_converter import ScriptConverter

def main():
    import sys
    import os
    
    # Print environment info
    sys.stderr.write(f"Python executable: {sys.executable}\n")
    sys.stderr.write(f"Current directory: {os.getcwd()}\n")
    sys.stderr.write(f"Environment variables: {dict(os.environ)}\n")
    sys.stderr.flush()
    
    sys.stderr.write("Starting script conversion...\n")
    sys.stderr.flush()
    converter = ScriptConverter()
    script_dir = Path.cwd()
    shell_path = script_dir / 'install.sh'
    batch_path = script_dir / 'release' / 'erasmus_v0.0.1.bat'

    # Print function templates
    sys.stderr.write("Function templates in converter:\n")
    for name, template in converter.function_templates.items():
        sys.stderr.write(f"- {name}: {len(template)} bytes\n")
    sys.stderr.flush()

    sys.stderr.write(f"Shell script path: {shell_path}\n")
    sys.stderr.write(f"Batch script path: {batch_path}\n")
    sys.stderr.write(f"Shell script exists: {shell_path.exists()}\n")
    sys.stderr.write(f"Batch script exists: {batch_path.exists()}\n")
    sys.stderr.flush()

    try:
        if not shell_path.exists():
            print(f"Shell script not found at: {shell_path}")
            return 1

        shell_content = shell_path.read_text(encoding='utf-8')
        print(f"Read {len(shell_content)} bytes from shell script")

        print("Converting shell script to batch script...")
        batch_content = converter.convert_script(shell_content)
        print(f"Generated {len(batch_content)} bytes of batch script")

        batch_path.parent.mkdir(parents=True, exist_ok=True)
        batch_path.write_text(batch_content, encoding='utf-8')
        print(f"Successfully wrote batch script to: {batch_path}")
        return 0
    except Exception as e:
        print(f"Error converting script: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    main()

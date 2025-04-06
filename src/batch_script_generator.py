import os
from pathlib import Path
from typing import Optional
from openai import OpenAI
from script_converter import ScriptConverter
from dotenv import load_dotenv
from .get_openai_creds import prompt_openai_credentials

load_dotenv()

class BatchScriptGenerator:
    client: OpenAI
    model: str
    version: str
    shell_script_path: Path
    release_path: Path
    shell_output_path: Path
    bat_output_path: Path

    def __init__(
        self, 
        api_key: Optional[str] = None, 
        base_url: Optional[str] = None, 
        model: Optional[str] = None, 
        version: Optional[str] = None,
        shell_script_path: Optional[str] = None, 
        release_path: Optional[str] = None
    ):
        """Initialize the batch script generator with optional API key."""
        self.client = self.openai_client(api_key, base_url)
        self.model = model or os.getenv('OPENAI_MODEL')
        self.version = version or os.getenv('VERSION')
        self.pwd = Path.cwd()
        self.configure_paths(shell_script_path, release_path)

    def openai_client(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> OpenAI:
        key = api_key or os.getenv('OPENAI_API_KEY')
        base = base_url or os.getenv('OPENAI_BASE_URL')
        
        print(f"Initializing OpenAI client with base URL: {base}")
        
        if not key:
            print("API key not found. Prompting for credentials...")
            prompt_openai_credentials()
            key = os.getenv('OPENAI_API_KEY')
        
        if not key:
            raise ValueError("No OpenAI API key found even after prompting")
        
        return OpenAI(api_key=key, base_url=base)

    def configure_paths(self, shell_script_path: Optional[str | Path] = None, release_path: Optional[str | Path] = None):
        """Configure input and output paths for script generation.
        
        Args:
            shell_script_path: Path to source shell script, defaults to './install.sh'
            release_path: Path to output directory, defaults to './release'
        """
        # Set and validate shell script path
        self.shell_script_path = Path(shell_script_path or 'install.sh')
        if not self.shell_script_path.exists():
            raise FileNotFoundError(f"Shell script not found: {self.shell_script_path}")

        # Set up release directory
        self.release_path = Path(release_path or 'release')
        self.release_path.mkdir(parents=True, exist_ok=True)

        # Configure output paths
        self.shell_output_path = self.release_path / f"erasmus_v{self.version}.sh"
        self.bat_output_path = self.release_path / f"erasmus_v{self.version}.bat"

    def read_shell_script(self, path: Path) -> str:
        """Read the content of a shell script file."""
        try:
            return path.read_text(encoding='utf-8')
        except Exception as e:
            raise Exception(f"Failed to read shell script {path}: {str(e)}")

    def generate_batch_script(self, shell_script_content: str) -> str:
        """Convert shell script to batch script using our custom converter."""
        print("\nGenerating batch script...")
        converter = ScriptConverter()
        return converter.convert_script(shell_script_content)

    def convert(
        self,
        shell_script_path: Optional[str | Path] = None, 
        bat_output_path: Optional[str | Path] = None, 
        sh_output_path: Optional[str | Path] = None
    ) -> tuple[Path, Path]:
        """Convert shell script to batch script and save both scripts.

        Args:
            shell_script_path: Optional override for source shell script path
            bat_output_path: Optional override for batch script output path
            sh_output_path: Optional override for shell script output path

        Returns:
            Tuple of (batch_script_path, shell_script_path)
        """
        # Update paths if provided
        if shell_script_path:
            self.shell_script_path = Path(shell_script_path)
        if bat_output_path:
            self.bat_output_path = Path(bat_output_path)
        if sh_output_path:
            self.shell_output_path = Path(sh_output_path)

        # Read and convert the script
        shell_content = self.read_shell_script(self.shell_script_path)
        batch_content = self.generate_batch_script(shell_content)

        # Save both scripts
        self.save_script(batch_content, self.bat_output_path)
        self.save_script(shell_content, self.shell_output_path)

        return self.bat_output_path, self.shell_output_path

    def save_script(self, content: str, output_path: Path) -> bool:
        """Save the converted script to the specified output path."""
        try:
            print(f"\nSaving script to {output_path}")
            output_path.write_text(content, encoding='utf-8')
            print(f"Successfully saved {len(content)} characters to {output_path}")
            return True
        except Exception as e:
            print(f"Failed to save script to {output_path}: {str(e)}")
            return False

def main():
    """Main function to demonstrate usage."""
    try:
        print("\nStarting batch script generation...")
        generator = BatchScriptGenerator()
        print("\nConverting shell script to batch...")
        bat_path, sh_path = generator.convert()
        print(f"\nGeneration complete!")
        print(f"Batch script path: {bat_path}")
        print(f"Shell script path: {sh_path}")
    except Exception as e:
        print(f"\nError generating script: {str(e)}")
        return 1
    return 0

if __name__ == '__main__':
    main()
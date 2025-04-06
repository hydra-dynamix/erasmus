import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OPENAI_API_KEY')
if not API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

BASE_URL = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"

MODEL = os.getenv("OPENAI_MODEL") or "gpt-4"

from openai import OpenAI

class BatchScriptGenerator:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the batch script generator with optional API key."""
        self.client = OpenAI(api_key=api_key or API_KEY, base_url=BASE_URL)

    def read_shell_script(self, shell_script_path: str) -> str:
        """Read the content of a shell script file."""
        with open(shell_script_path, 'r', encoding='utf-8') as f:
            return f.read()

    def generate_batch_script(self, shell_script_content: str) -> str:
        """Convert shell script to batch script using OpenAI."""
        prompt = (
            "Convert the following shell script to a Windows batch script (.bat). "
            "Maintain equivalent functionality while using Windows-specific commands "
            "and syntax. Include proper error handling and Windows-specific path handling. "
            "Return only the batch script content, no explanations.\n\n"
            f"Shell script:\n{shell_script_content}"
        )

        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a script conversion expert. Provide only the converted script content without any additional text or markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2  # Lower temperature for more consistent output
        )

        return response.choices[0].message.content.strip()

    def convert_and_save(self, shell_script_path: str, output_path: Optional[str] = None) -> str:
        """Convert shell script to batch script and save it.

        Args:
            shell_script_path: Path to the source shell script
            output_path: Optional custom output path for the batch script

        Returns:
            Path to the generated batch script
        """
        if not os.path.exists(shell_script_path):
            raise FileNotFoundError(f"Shell script not found: {shell_script_path}")

        # If no output path specified, create one based on input path
        if output_path is None:
            input_path = Path(shell_script_path)
            output_path = str(input_path.parent / f"{input_path.stem}.bat")

        # Read and convert the script
        shell_content = self.read_shell_script(shell_script_path)
        batch_content = self.generate_batch_script(shell_content)

        # Save the converted script
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)

        return output_path

def main():
    """Main function to demonstrate usage."""
    try:
        generator = BatchScriptGenerator()
        script_dir = Path(__file__).parent.parent
        shell_script_path = script_dir / 'install.sh'
        output_path = script_dir / 'install.bat'

        generated_path = generator.convert_and_save(
            str(shell_script_path),
            str(output_path)
        )
        print(f"Successfully generated batch script at: {generated_path}")

    except Exception as e:
        print(f"Error generating batch script: {str(e)}")

if __name__ == '__main__':
    main()
import base64
import hashlib
import json
from pathlib import Path
from typing import Dict, Tuple


def embed_file(file_path: Path) -> Tuple[str, str]:
    """Encode a file as base64 and calculate its SHA-256 hash.
    
    Args:
        file_path: Path to the file to embed
        
    Returns:
        Tuple containing (base64_encoded_content, sha256_hash)
    """
    with open(file_path, "rb") as f:
        content = f.read()
        # Calculate SHA-256 hash
        file_hash = hashlib.sha256(content).hexdigest()
        # Encode content as base64
        encoded = base64.b64encode(content).decode("utf-8")
    return encoded, file_hash

def handle_registry(registry_data: Dict[str, Dict[str, str]], registry_path: Path) -> Tuple[str, str]:
    try:
        registry_data["mcpServers"]["github"]["server"]["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"] = "GITHUB_PERSONAL_ACCESS_TOKEN"
        sha_hash = hashlib.sha256(json.dumps(registry_data).encode("utf-8")).hexdigest()
        content = base64.b64encode(json.dumps(registry_data).encode("utf-8")).decode("utf-8")
        return content, sha_hash
    except Exception as error:
        print(f"Failed to load registry from {registry_path}: {error}")
        return None, None

def collect_dot_erasmus_embedded_files() -> Dict[str, Dict[str, str]]:
    """
    Collect all files under .erasmus in the project root and return a dict of 
    {relative_path: {"content": base64_content, "hash": sha256_hash}}.
    
    Returns:
        Dictionary mapping file paths to their encoded content and SHA-256 hash
    """
    erasmus_dir = Path.cwd() / ".erasmus"
    embedded = {}
    if not erasmus_dir.exists():
        return embedded

    ignore_patterns = [".erasmus/context/", ".erasmus/protocols/", ".erasmus/logs/"]
    def walk_dir(current_path: Path):
        for entry in current_path.iterdir():
            if any(pattern in str(entry) for pattern in ignore_patterns):
                continue
            if "registry.json" == entry.name:
                print("Found registry.json")
                registry_content, registry_hash = handle_registry(json.loads(entry.read_text()), entry)
                if registry_content and registry_hash:
                    embedded[str(entry.relative_to(erasmus_dir))] = {
                        "content": registry_content,
                        "hash": registry_hash
                    }
                continue
                
            if entry.is_file():
                content, file_hash = embed_file(entry)
                embedded[str(entry.relative_to(erasmus_dir))] = {
                    "content": content,
                    "hash": file_hash
                }
            elif entry.is_dir():
                walk_dir(entry)
    walk_dir(erasmus_dir)
    return embedded

def add_embedded_files():#output_path: Path):
    """Add embedded files to the output bundle with SHA-256 hash validation.
    """
    # Args:
    #     output_path: Path to the output bundle file
    # """
    # Collect embedded files from .erasmus directory
    embedded = collect_dot_erasmus_embedded_files()
    
    # Read the original bundle content
    # original_content = output_path.read_text()
    
    # Add the bundle itself to the embedded files
    # content, file_hash = embed_file(output_path)
    # embedded["erasmus.py"] = {
        # "content": content,
        # "hash": file_hash
    # }
    
    # Create the extraction code block with hash validation
    code_block = f'''
def validate_and_extract_files(encoded_files):
    """Extract embedded files with SHA-256 hash validation.
    
    Args:
        encoded_files: Dictionary of {{path: {{"content": base64_content, "hash": sha256_hash}}}}
    """
    import json
    import base64
    import hashlib
    import sys
    from pathlib import Path

    erasmus_path = Path.cwd() / ".erasmus"

    logs_path = erasmus_path / "logs"
    logs_path.mkdir(parents=True, exist_ok=True)
    gitkeep_path = logs_path / ".gitkeep"
    gitkeep_path.write_text("")

    context_path = erasmus_path / "context"
    context_path.mkdir(parents=True, exist_ok=True)
    gitkeep_path = context_path / ".gitkeep"
    gitkeep_path.write_text("")
    
    protocol_path = erasmus_path / "protocol"
    protocol_path.mkdir(parents=True, exist_ok=True)
    gitkeep_path = protocol_path / ".gitkeep"
    gitkeep_path.write_text("")
    
    print("Validating and extracting embedded files...")
    for path, file_data in encoded_files.items():
        path = Path.cwd() / ".erasmus" / path
        path.parent.mkdir(parents=True, exist_ok=True)
        content = base64.b64decode(file_data["content"])
        expected_hash = file_data["hash"]
        
        # Validate hash
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != expected_hash:
            print(f"ERROR: Hash mismatch for {{path}}")
            print(f"Expected: {{expected_hash}}")
            print(f"Actual: {{actual_hash}}")
            print("File may be corrupted or tampered with. Aborting.")
            sys.exit(1)
        
        # Create directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(path, "wb") as f:
            f.write(content)
        print(f"Extracted: {{path}} (hash verified)")

# Dictionary of embedded files with their content and hash
encoded_files = {json.dumps(embedded, indent=4)}
erasmus_path = Path.cwd() / ".erasmus"
if not erasmus_path.exists():
    erasmus_path.mkdir(parents=True, exist_ok=True)
# Extract all files with hash validation
validate_and_extract_files(encoded_files)
'''
    # print(f"Added embedded files with SHA-256 hash validation to {output_path}")
    print(f"Total embedded files: {len(embedded)}")
    return code_block
    
    


if __name__ == "__main__":
    # Example usage
    output_path = Path.cwd() / "releases" / "erasmus" / "0.0.0" / "erasmus_bundle_v0.0.0.py"
    if output_path.exists():
        code_block = add_embedded_files(output_path)
        print(f"Successfully added embedded files to {output_path}")
        print(code_block)
    else:
        print(f"Error: {output_path} does not exist")

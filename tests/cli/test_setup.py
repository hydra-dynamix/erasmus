"""Tests for the setup command."""
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from erasmus.cli.setup import setup, validate_base_url, validate_ide_env


@pytest.fixture
def env_example_content():
    return (
        "IDE_ENV=cursor\n"
        "GIT_TOKEN=sk-git-token\n"
        "OPENAI_API_KEY=sk-1234\n"
        "OPENAI_BASE_URL=https://api.openai.com/v1\n"
        "OPENAI_MODEL=gpt-4o\n"
    )

@pytest.fixture
def runner():
    return CliRunner()

def test_validate_ide_env():
    """Test IDE_ENV validation."""
    # Test valid inputs
    assert validate_ide_env("cursor") == "cursor"
    assert validate_ide_env("C") == "cursor"
    assert validate_ide_env("windsurf") == "windsurf"
    assert validate_ide_env("W") == "windsurf"

    # Test invalid inputs
    with pytest.raises(ValueError):
        validate_ide_env("invalid")
    with pytest.raises(ValueError):
        validate_ide_env("x")

def test_validate_base_url():
    """Test OPENAI_BASE_URL validation."""
    # Test valid URLs
    assert validate_base_url("https://api.openai.com/v1") == "https://api.openai.com/v1"
    assert validate_base_url("http://localhost") == "http://localhost"
    assert validate_base_url("http://localhost:8000") == "http://localhost:8000"
    assert validate_base_url("http://localhost:8000/api") == "http://localhost:8000/api"

    # Test invalid URLs
    with pytest.raises(ValueError):
        validate_base_url("not-a-url")
    with pytest.raises(ValueError):
        validate_base_url("ftp://invalid-protocol")

@pytest.mark.parametrize("env_exists", [True, False])
def test_setup_command(runner, env_example_content, env_exists, tmp_path):
    """Test the setup command with and without existing .env."""
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        # Create .env.example
        with open(".env.example", "w") as f:
            f.write(env_example_content)

        # Create .env if testing existing case
        if env_exists:
            with open(".env", "w") as f:
                f.write(env_example_content)

        # Mock user input
        input_values = []
        if env_exists:
            input_values.append("y")  # Overwrite confirmation

        input_values.extend([
            "c",  # IDE_ENV
            "my-token",  # GIT_TOKEN
            "sk-mykey",  # OPENAI_API_KEY
            "http://localhost:8000",  # OPENAI_BASE_URL
            "gpt-4",  # OPENAI_MODEL
        ])

        with patch("rich.prompt.Prompt.ask", side_effect=input_values):
            result = runner.invoke(setup)

        assert result.exit_code == 0
        assert Path(".env").exists()

        # Verify .env contents
        with open(".env") as f:
            env_contents = f.read()
            assert "IDE_ENV=cursor" in env_contents
            assert "GIT_TOKEN=my-token" in env_contents
            assert "OPENAI_API_KEY=sk-mykey" in env_contents
            assert "OPENAI_BASE_URL=http://localhost:8000" in env_contents
            assert "OPENAI_MODEL=gpt-4" in env_contents

def test_setup_invalid_inputs(runner, env_example_content, tmp_path):
    """Test the setup command with invalid inputs that are then corrected."""
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        # Create .env.example
        with open(".env.example", "w") as f:
            f.write(env_example_content)

        # Mock user input sequence: invalid then valid for IDE_ENV and BASE_URL
        input_values = [
            "x",  # Invalid IDE_ENV
            "c",  # Valid IDE_ENV
            "my-token",  # GIT_TOKEN
            "sk-mykey",  # OPENAI_API_KEY
            "invalid-url",  # Invalid BASE_URL
            "http://localhost:8000",  # Valid BASE_URL
            "gpt-4",  # OPENAI_MODEL
        ]

        with patch("rich.prompt.Prompt.ask", side_effect=input_values):
            result = runner.invoke(setup)

        assert result.exit_code == 0
        assert Path(".env").exists()

        # Verify .env contents
        with open(".env") as f:
            env_contents = f.read()
            assert "IDE_ENV=cursor" in env_contents
            assert "OPENAI_BASE_URL=http://localhost:8000" in env_contents

def test_setup_missing_env_example(runner, env_example_content, tmp_path):
    """Test setup behavior when .env.example is missing."""
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        # Mock user choosing to create default .env.example
        with patch("click.confirm", return_value=True):
            result = runner.invoke(setup)

        assert result.exit_code == 0
        assert Path(".env.example").exists()

        # Verify .env.example contents
        with open(".env.example") as f:
            contents = f.read()
            assert "IDE_ENV=cursor" in contents
            assert "OPENAI_BASE_URL=https://api.openai.com/v1" in contents

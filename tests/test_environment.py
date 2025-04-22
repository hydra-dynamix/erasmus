import os
import pytest
from erasmus.environment import (
    EnvironmentConfig,
    EnvironmentError,
    is_sensitive_variable,
    mask_sensitive_value,
)


@pytest.fixture
def env_config():
    """Create an EnvironmentConfig instance for testing."""
    return EnvironmentConfig()


@pytest.fixture
def sample_env_file(tmp_path):
    """Create a sample .env file for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text("""# Test environment variables
TEST_VAR1=value1
TEST_VAR2=value2
# Commented variable
# TEST_VAR3=value3
""")
    return env_file


def test_define_required(env_config):
    """Test defining a required environment variable."""
    env_config.define_required("TEST_VAR", str)
    assert "TEST_VAR" in env_config._definitions
    assert env_config._definitions["TEST_VAR"].required is True


def test_define_optional(env_config):
    """Test defining an optional environment variable."""
    env_config.define_optional("TEST_VAR", str)
    assert "TEST_VAR" in env_config._definitions
    assert env_config._definitions["TEST_VAR"].required is False


def test_set_variable(env_config):
    """Test setting an environment variable."""
    env_config.define_required("TEST_VAR", str)
    env_config.set("TEST_VAR", "test_value")
    assert env_config.get("TEST_VAR") == "test_value"


def test_set_undefined_variable(env_config):
    """Test setting an undefined variable."""
    with pytest.raises(EnvironmentError):
        env_config.set("UNDEFINED_VAR", "test_value")


def test_set_invalid_type(env_config):
    """Test setting a variable with invalid type."""
    env_config.define_required("TEST_VAR", int)
    with pytest.raises(EnvironmentError):
        env_config.set("TEST_VAR", "not_an_integer")


def test_get_variable(env_config):
    """Test getting an environment variable."""
    env_config.define_required("TEST_VAR", str)
    env_config.set("TEST_VAR", "test_value")
    assert env_config.get("TEST_VAR") == "test_value"


def test_get_nonexistent_variable(env_config):
    """Test getting a nonexistent variable."""
    assert env_config.get("NONEXISTENT_VAR") is None
    assert env_config.get("NONEXISTENT_VAR", "default") == "default"


def test_get_masked_sensitive(env_config):
    """Test getting a masked sensitive variable."""
    env_config.define_required("API_KEY", str)
    env_config.set("API_KEY", "secret_key_123")
    assert env_config.get_masked("API_KEY") == "se***"


def test_get_masked_non_sensitive(env_config):
    """Test getting a masked non-sensitive variable."""
    env_config.define_required("PUBLIC_VAR", str)
    env_config.set("PUBLIC_VAR", "public_value")
    assert env_config.get_masked("PUBLIC_VAR") == "public_value"


def test_load_from_file(env_config, sample_env_file):
    """Test loading environment variables from a file."""
    env_config.define_required("TEST_VAR1", str)
    env_config.define_required("TEST_VAR2", str)
    env_config.load_from_file(sample_env_file)
    assert env_config.get("TEST_VAR1") == "value1"
    assert env_config.get("TEST_VAR2") == "value2"


def test_load_from_nonexistent_file(env_config, tmp_path):
    """Test loading from a nonexistent file."""
    nonexistent_file = tmp_path / "nonexistent.env"
    with pytest.raises(EnvironmentError):
        env_config.load_from_file(nonexistent_file)


def test_load_from_system(env_config, monkeypatch):
    """Test loading environment variables from system environment."""
    env_config.define_required("TEST_VAR", str)
    monkeypatch.setenv("TEST_VAR", "system_value")
    env_config.load_from_system()
    assert env_config.get("TEST_VAR") == "system_value"


def test_validate_all_required(env_config):
    """Test validation with all required variables set."""
    env_config.define_required("TEST_VAR1", str)
    env_config.define_required("TEST_VAR2", str)
    env_config.set("TEST_VAR1", "value1")
    env_config.set("TEST_VAR2", "value2")
    env_config.validate()  # Should not raise an exception


def test_validate_missing_required(env_config):
    """Test validation with missing required variables."""
    env_config.define_required("TEST_VAR1", str)
    env_config.define_required("TEST_VAR2", str)
    env_config.set("TEST_VAR1", "value1")
    with pytest.raises(EnvironmentError):
        env_config.validate()


def test_merge_configs(env_config):
    """Test merging two environment configurations."""
    env_config.define_required("TEST_VAR1", str)
    env_config.set("TEST_VAR1", "value1")

    other_config = EnvironmentConfig()
    other_config.define_required("TEST_VAR2", str)
    other_config.set("TEST_VAR2", "value2")

    env_config.merge(other_config)
    assert env_config.get("TEST_VAR1") == "value1"
    assert env_config.get("TEST_VAR2") == "value2"


def test_is_sensitive_variable():
    """Test detection of sensitive variable names."""
    assert is_sensitive_variable("API_KEY") is True
    assert is_sensitive_variable("SECRET_TOKEN") is True
    assert is_sensitive_variable("PASSWORD") is True
    assert is_sensitive_variable("PUBLIC_VAR") is False


def test_mask_sensitive_value():
    """Test masking of sensitive values."""
    assert mask_sensitive_value("secret_key_123") == "se***"
    assert mask_sensitive_value("ab") == "***"
    assert mask_sensitive_value("") == "***"

import os
import pytest
from unittest.mock import patch
from helpers.placeholder_manager import PlaceholderManager, get_simple_placeholder_from_name


@pytest.fixture
def sample_config():
    return {"BASE_URL": "https://demo.test"}


@pytest.fixture
def manager(sample_config):
    return PlaceholderManager(sample_config)


# --------------------------
# Helper
# --------------------------

def test_get_simple_placeholder_from_name():
    assert get_simple_placeholder_from_name("path") == "#PATH#"
    assert get_simple_placeholder_from_name("user_id") == "#USER_ID#"


# --------------------------
# Add / Remove Placeholders
# --------------------------

def test_add_placeholder_with_value(manager):
    manager.add_placeholder("path", "/home")
    assert manager.placeholders_map == {"#PATH#": "/home"}


def test_add_placeholder_without_value(manager):
    manager.add_placeholder("url")
    assert "#URL#" in manager.placeholders_map
    assert manager.placeholders_map["#URL#"] is None


def test_remove_existing_placeholder(manager):
    manager.add_placeholder("token", "abc123")
    removed = manager.remove_placeholder("token")
    assert removed == "abc123"
    assert "#TOKEN#" not in manager.placeholders_map


def test_remove_nonexistent_placeholder(manager):
    removed = manager.remove_placeholder("nonexistent")
    assert removed is None


# --------------------------
# Replace simple placeholders → values
# --------------------------

@patch("helpers.placeholder_manager.get_effective_config_value", return_value="CONFIG_VALUE")
def test_replace_simple_placeholder_with_value(mock_effective, manager):
    manager.add_placeholder("key", "VALUE")
    text = "API=#KEY#"
    result = manager.replace_placeholders_with_values(text)
    assert result == "API=VALUE"
    mock_effective.assert_not_called()


@patch("helpers.placeholder_manager.get_effective_config_value", return_value="CONFIG_VALUE")
def test_replace_simple_placeholder_dynamic(mock_effective, manager):
    # value is None → should call get_effective_config_value
    manager.add_placeholder("key")
    text = "API=#KEY#"
    result = manager.replace_placeholders_with_values(text)
    assert result == "API=CONFIG_VALUE"
    mock_effective.assert_called_once()


@patch("helpers.placeholder_manager.get_effective_config_value", return_value="resolved")
def test_nested_placeholder_replacement(mock_effective, manager):
    # nested placeholder value points to another placeholder
    manager.add_placeholder("A", "#B#")
    manager.add_placeholder("B", "ok")
    text = "Test: #A#"
    result = manager.replace_placeholders_with_values(text)
    assert result == "Test: ok"


# --------------------------
# Replace values → placeholders
# --------------------------

@patch("helpers.placeholder_manager.get_effective_config_value", return_value="CONFIG_VALUE")
def test_replace_values_with_simple_placeholders(mock_effective, manager):
    manager.add_placeholder("key", "VALUE")
    text = "API=VALUE"
    result = manager.replace_values_with_placeholders(text)
    assert result == "API=#KEY#"


@patch("helpers.placeholder_manager.get_effective_config_value", return_value="CONFIG_VALUE")
def test_replace_values_with_dynamic_value(mock_effective, manager):
    manager.add_placeholder("key")
    text = "API=CONFIG_VALUE"
    result = manager.replace_values_with_placeholders(text)
    assert result == "API=#KEY#"
    mock_effective.assert_called_once()


# --------------------------
# Environment variable placeholders
# --------------------------

def test_replace_placeholder_with_env_variable(monkeypatch, manager):
    """
    Verify that a placeholder with no direct value is resolved
    from an environment variable using get_effective_config_value().
    """
    # Simulate an environment variable
    monkeypatch.setenv("PATH_ENV", "/usr/local/bin")

    # Patch get_effective_config_value to return the environment variable
    with patch("helpers.placeholder_manager.get_effective_config_value",
               side_effect=lambda key, config: os.getenv(key.strip("#"))):
        manager.add_placeholder("PATH_ENV")  # no value → dynamic lookup
        text = "System path is #PATH_ENV#"
        result = manager.replace_placeholders_with_values(text)

    assert result == "System path is /usr/local/bin"

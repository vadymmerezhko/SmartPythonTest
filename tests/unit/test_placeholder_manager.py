import os
import pytest
from unittest.mock import patch
from helpers.placeholder_manager import (
    PlaceholderManager,
    get_simple_placeholder_from_name
)


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
    assert manager.placeholders_map == {"path": "/home"}


def test_add_placeholder_without_value(manager):
    manager.add_placeholder("url")
    assert "url" in manager.placeholders_map
    assert manager.placeholders_map["url"] is None


def test_remove_existing_placeholder(manager):
    manager.add_placeholder("token", "abc123")
    manager.remove_placeholder("token")
    assert "token" not in manager.placeholders_map


def test_remove_nonexistent_placeholder(manager):
    # Should not raise an error
    manager.remove_placeholder("nonexistent")
    assert "nonexistent" not in manager.placeholders_map


# --------------------------
# Replace placeholders → values
# --------------------------

@patch("helpers.placeholder_manager.get_effective_config_value", return_value="CONFIG_VALUE")
def test_replace_placeholder_with_value(mock_effective, manager):
    manager.add_placeholder("key", "VALUE")
    text = "API=#KEY#"
    result = manager.replace_placeholders_with_values(text)
    assert result == "API=VALUE"
    mock_effective.assert_not_called()


@patch("helpers.placeholder_manager.get_effective_config_value", return_value="CONFIG_VALUE")
def test_replace_placeholder_dynamic(mock_effective, manager):
    manager.add_placeholder("key")
    text = "API=#KEY#"
    result = manager.replace_placeholders_with_values(text)
    assert result == "API=CONFIG_VALUE"
    mock_effective.assert_called_once_with("key", manager.config)


@patch("helpers.placeholder_manager.get_effective_config_value", return_value="resolved")
def test_nested_placeholder_replacement(mock_effective, manager):
    # Nested replacement: A → B → ok
    manager.add_placeholder("A", "#B#")
    manager.add_placeholder("B", "ok")
    text = "Test: #A#"
    result = manager.replace_placeholders_with_values(text)
    assert result == "Test: ok"
    mock_effective.assert_not_called()


# --------------------------
# Replace values → placeholders
# --------------------------

@patch("helpers.placeholder_manager.get_effective_config_value", return_value="CONFIG_VALUE")
def test_replace_values_with_placeholders(mock_effective, manager):
    manager.add_placeholder("key", "VALUE")
    text = "API=VALUE"
    result = manager.replace_values_with_placeholders(text)
    assert result == "API=#KEY#"
    mock_effective.assert_not_called()


@patch("helpers.placeholder_manager.get_effective_config_value", return_value="CONFIG_VALUE")
def test_replace_dynamic_values_with_placeholders(mock_effective, manager):
    manager.add_placeholder("key")  # no direct value
    text = "API=CONFIG_VALUE"
    result = manager.replace_values_with_placeholders(text)
    assert result == "API=#KEY#"
    mock_effective.assert_called_once_with("key", manager.config)


# --------------------------
# Environment variable placeholders
# --------------------------

def test_replace_placeholder_with_env_variable(monkeypatch, manager):
    """
    Verify that a placeholder with no direct value is resolved
    from an environment variable using get_effective_config_value().
    """
    monkeypatch.setenv("PATH_ENV", "/usr/local/bin")

    with patch("helpers.placeholder_manager.get_effective_config_value",
               side_effect=lambda key, cfg: os.getenv(key.upper())):
        manager.add_placeholder("PATH_ENV")  # no value → dynamic lookup
        text = "System path is #PATH_ENV#"
        result = manager.replace_placeholders_with_values(text)

    assert result == "System path is /usr/local/bin"

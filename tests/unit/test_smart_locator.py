import pytest
from unittest.mock import MagicMock, patch
from wrappers.smart_locator import SmartLocator, FIXED_SELECTORS, FIXED_VALUES, FIXED_KEYWORDS


@pytest.fixture(autouse=True)
def clear_globals():
    FIXED_SELECTORS.clear()
    FIXED_VALUES.clear()
    FIXED_KEYWORDS.clear()
    yield
    FIXED_SELECTORS.clear()
    FIXED_VALUES.clear()
    FIXED_KEYWORDS.clear()

@pytest.fixture
def dummy_owner():
    page = MagicMock()
    config = {"record_mode": False}
    return type("DummyOwner", (), {"page": page, "config": config})

@pytest.fixture
def dummy_placeholder_manager(monkeypatch):
    fake_pm = MagicMock()
    monkeypatch.setattr("wrappers.smart_locator.PlaceholderManager", lambda cfg: fake_pm)
    return fake_pm

def test_constructor_sets_cache_key_and_field_info(dummy_owner, dummy_placeholder_manager):
    owner = dummy_owner()
    locator = SmartLocator(owner, "#login")
    assert locator.selector == "#login"
    assert locator.cache_key.startswith(owner.__class__.__name__)
    assert isinstance(locator.placeholder_manager, MagicMock)

def test_set_keyword_updates_selector_and_cache(dummy_owner, dummy_placeholder_manager):
    owner = dummy_owner()
    locator = SmartLocator(owner, "input#KEYWORD#")
    locator.set_keyword("username")
    assert locator.keyword == "username"
    assert "username" in locator.selector
    assert locator.cache_key in FIXED_SELECTORS

def test_get_keyword_returns_expected(dummy_owner, dummy_placeholder_manager):
    owner = dummy_owner()
    locator = SmartLocator(owner, "#login")
    locator.keyword = "abc"
    assert locator.get_keyword() == "abc"

def test_add_and_remove_placeholder_calls_manager(dummy_owner, dummy_placeholder_manager):
    owner = dummy_owner()
    locator = SmartLocator(owner, "#login")
    locator.add_placeholder("x", "y")
    locator.remove_placeholder("x")
    dummy_placeholder_manager.add_placeholder.assert_called_once_with("x", "y")
    dummy_placeholder_manager.remove_placeholder.assert_called_once_with("x")

@patch("wrappers.smart_locator.handle_missing_locator", return_value="#fixed")
@patch("wrappers.smart_locator.update_source_file")
def test_fix_locator_updates_cache(mock_update, mock_handle, dummy_owner, dummy_placeholder_manager):
    owner = dummy_owner()
    locator = SmartLocator(owner, "#old")
    result = locator.fix_locator()
    assert FIXED_SELECTORS[locator.cache_key] == "#fixed"
    owner.page.locator.assert_called_with("#fixed")
    assert result == owner.page.locator.return_value

@patch("wrappers.smart_locator.fix_noname_parameter_value", return_value=("TYPE", "fixed"))
def test_validate_arguments_fixes_none_and_replaces_placeholders(mock_fix, dummy_owner, dummy_placeholder_manager):
    owner = dummy_owner()
    owner.config["record_mode"] = True
    dummy_placeholder_manager.replace_placeholders_with_values.side_effect = lambda v: v + "_repl"

    locator = SmartLocator(owner, "#login")
    args, kwargs = locator.validate_arguments((None, "abc"), {})
    assert args[0] == "fixed_repl"
    assert args[1] == "abc_repl"
    assert locator.cache_key in FIXED_VALUES

@patch("wrappers.smart_locator.fix_noname_parameter_value", return_value=("KEY", "new_keyword"))
def test_validate_keyword_value_none_triggers_fix(mock_fix, dummy_owner, dummy_placeholder_manager):
    owner = dummy_owner()
    owner.config["record_mode"] = True
    locator = SmartLocator(owner, "#sel")
    locator.keyword = None
    locator.validate_keyword_value()
    assert locator.keyword == "new_keyword"
    assert locator.cache_key in FIXED_KEYWORDS

def test_validate_keyword_value_uses_cached_keyword(dummy_owner, dummy_placeholder_manager):
    owner = dummy_owner()
    FIXED_KEYWORDS["DummyOwner.unknown_field"] = ("KEY", "cached_val")
    locator = SmartLocator(owner, "#sel")
    locator.keyword = None
    locator.validate_keyword_value()
    assert locator.keyword == "cached_val"

def test_locator_property_calls_page_locator(dummy_owner, dummy_placeholder_manager):
    owner = dummy_owner()
    locator = SmartLocator(owner, "#x")
    result = locator.locator
    owner.page.locator.assert_called_with("#x")
    assert result == owner.page.locator.return_value

@patch("wrappers.smart_locator.normalize_args", return_value=(("A",), {}))
def test_getattr_wraps_callable_and_handles_exception(mock_norm, dummy_owner, dummy_placeholder_manager):
    owner = dummy_owner()
    owner.config["record_mode"] = True
    inner = MagicMock()
    inner.side_effect = Exception("No node found")  # triggers fix_locator
    owner.page.locator.return_value.click = inner

    locator = SmartLocator(owner, "#login")
    with patch.object(locator, "fix_locator") as fix_mock:
        fix_mock.return_value.click.return_value = "OK"
        result = locator.click()
        assert result == "OK"
        fix_mock.assert_called_once()

def test_str_and_repr_show_selector(dummy_owner, dummy_placeholder_manager):
    owner = dummy_owner()
    locator = SmartLocator(owner, "#abc")
    s = str(locator)
    assert "SmartLocator" in s
    assert "#abc" in s
    assert repr(locator) == s

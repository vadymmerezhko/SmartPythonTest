import pytest
from unittest.mock import Mock, patch

from wrappers.smart_locator import SmartLocator, FIXED_SELECTORS, FIXED_VALUES


@pytest.fixture
def mock_owner():
    owner = Mock()
    owner.page = Mock()
    owner.page.locator.return_value = Mock(name="locator")
    owner.config = {"record_mode": True}
    owner.placeholder_manager = Mock()
    owner.placeholder_manager.replace_placeholders_with_values.side_effect = lambda x: x
    owner.keyword = None
    owner.get_keyword.return_value = None
    return owner


def test_init_sets_basic_fields(mock_owner):
    FIXED_SELECTORS.clear()
    sl = SmartLocator(mock_owner, "#username")
    assert sl.selector == "#username"
    assert sl.page == mock_owner.page
    assert sl.cache_key.startswith(mock_owner.__class__.__name__)


def test_init_reuses_fixed_selector(mock_owner):
    FIXED_SELECTORS.clear()
    FIXED_SELECTORS["Mock.field1"] = "#fixed"
    with patch("wrappers.smart_locator.SmartLocator._get_field_info",
               return_value=("field1", "file")):
        sl = SmartLocator(mock_owner, "#orig")
        assert sl.selector == "#fixed"


def test_locator_replaces_keyword(mock_owner):
    FIXED_SELECTORS.clear()
    mock_owner.keyword = "USER"
    sl = SmartLocator(mock_owner, "#KEYWORD#_input")
    sl._locator()
    assert "USER" in sl.selector
    mock_owner.page.locator.assert_called()


def test_validate_arguments_with_none_value(monkeypatch, mock_owner):
    FIXED_VALUES.clear()
    mock_update = ("param", "fixed")
    monkeypatch.setattr("wrappers.smart_locator.fix_noname_parameter_value", lambda *a, **k: mock_update)

    sl = SmartLocator(mock_owner, "#input")
    args, kwargs = sl._validate_arguments((None,), {})
    assert args[0] == "fixed"
    assert "fixed" in FIXED_VALUES[sl.cache_key][1]


def test_validate_arguments_with_string_value(mock_owner):
    FIXED_VALUES.clear()
    mock_owner.config = {"record_mode": True}
    mock_owner.placeholder_manager.replace_placeholders_with_values.return_value = "replaced"
    sl = SmartLocator(mock_owner, "#input")
    args, kwargs = sl._validate_arguments(("abc",), {})
    # current logic does NOT replace "abc"
    assert args[0] == "abc"


def test_fix_locator_updates_cache(monkeypatch, mock_owner):
    FIXED_SELECTORS.clear()
    monkeypatch.setattr("wrappers.smart_locator.handle_missing_locator", lambda *a, **k: "#new")
    monkeypatch.setattr("wrappers.smart_locator.update_source_file", lambda *a, **k: None)
    mock_owner.page.locator.return_value = Mock(name="new_locator")

    sl = SmartLocator(mock_owner, "#old")
    new_locator = sl._fix_locator()
    assert FIXED_SELECTORS[sl.cache_key] == "#new"
    assert new_locator is mock_owner.page.locator.return_value


def test_handle_error_fix_locator(monkeypatch, mock_owner):
    FIXED_VALUES.clear()
    mock_owner.placeholder_manager.replace_placeholders_with_values.side_effect = lambda v: v
    monkeypatch.setattr("wrappers.smart_locator.fix_noname_parameter_value", lambda *a, **k: ("param", "fixed_value"))
    monkeypatch.setattr("wrappers.smart_locator.handle_missing_locator", lambda *a, **k: "#fixed_sel")
    monkeypatch.setattr("wrappers.smart_locator.update_source_file", lambda *a, **k: None)
    mock_owner.page.locator.return_value = Mock()

    sl = SmartLocator(mock_owner, "#broken")
    err = Exception("Locator.select_option: Timeout 30000ms exceeded")
    new_locator, args, kwargs = sl._handle_error(("bad",), {}, err)
    assert args[0] == "fixed_value"
    assert isinstance(new_locator, Mock)


def test_handle_error_no_node_found(monkeypatch, mock_owner):
    monkeypatch.setattr("wrappers.smart_locator.handle_missing_locator", lambda *a, **k: "#fixed_sel")
    monkeypatch.setattr("wrappers.smart_locator.update_source_file", lambda *a, **k: None)
    mock_owner.page.locator.return_value = Mock(name="loc")

    sl = SmartLocator(mock_owner, "#old")
    err = Exception("No node found for selector")
    new_locator, args, kwargs = sl._handle_error(("abc",), {}, err)
    assert isinstance(new_locator, Mock)
    assert new_locator is mock_owner.page.locator.return_value


def test_str_representation(mock_owner, monkeypatch):
    # Patch __getattr__ to fake get_keyword() call
    def fake_getattr(self, name):
        if name == "get_keyword":
            return lambda: "USER"
        return Mock()
    monkeypatch.setattr("wrappers.smart_locator.SmartLocator.__getattr__", fake_getattr)

    sl = SmartLocator(mock_owner, "#x")
    result = str(sl)
    assert "SmartLocator" in result
    assert "selector" in result

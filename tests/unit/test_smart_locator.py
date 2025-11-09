import pytest
from unittest.mock import Mock, patch
from wrappers.smart_locator import SmartLocator, FIXED_SELECTORS, FIXED_VALUES


@pytest.fixture
def mock_owner():
    """Creates a mocked owner object with all required fields."""
    owner = Mock()
    owner.page = Mock()
    owner.page.locator.return_value = Mock(name="locator")
    owner.config = {"record_mode": True}
    owner.placeholder_manager = Mock()
    owner.placeholder_manager.replace_placeholders_with_values.side_effect = lambda x: f"replaced:{x}"
    owner.keyword = None
    owner.get_keyword.return_value = None
    return owner


def test_init_sets_fields(mock_owner):
    FIXED_SELECTORS.clear()
    sl = SmartLocator(mock_owner, "#username")
    assert sl.selector == "#username"
    assert sl.page == mock_owner.page
    assert sl.config == {"record_mode": True}
    assert isinstance(sl.cache_key, str)
    assert sl.placeholder_manager == mock_owner.placeholder_manager


def test_init_reuses_fixed_selector(mock_owner):
    FIXED_SELECTORS.clear()
    FIXED_SELECTORS["Mock.field1"] = "#cached"
    with patch("wrappers.smart_locator.SmartLocator._get_field_info", return_value=("field1", "file.py")):
        sl = SmartLocator(mock_owner, "#old")
        assert sl.selector == "#cached"


def test_get_field_info_detects_assignment(monkeypatch, mock_owner):
    """Ensures _get_field_info can extract variable name from a simulated code context."""
    fake_stack = [Mock()]
    fake_stack[0].code_context = ["self.button = SmartLocator(self, '#btn')"]
    fake_stack[0].filename = "page.py"

    monkeypatch.setattr("inspect.stack", lambda: fake_stack)
    sl = SmartLocator(mock_owner, "#x")
    field, src = sl._get_field_info()
    assert field == "button"
    assert src == "page.py"


from common.constnts import KEYWORD_PLACEHOLDER


def test_locator_replaces_keyword(mock_owner):
    """Ensures selector placeholder is replaced with keyword string."""
    FIXED_SELECTORS.clear()
    mock_owner.keyword = "LOGIN"

    placeholder = KEYWORD_PLACEHOLDER  # use actual constant
    sl = SmartLocator(mock_owner, f"{placeholder}_input")
    result = sl._locator()

    expected = f"{mock_owner.keyword}_input"
    assert expected in sl.selector or sl.selector == expected
    mock_owner.page.locator.assert_called_once_with(sl.selector)
    assert result == mock_owner.page.locator.return_value



def test_validate_arguments_replaces_none(monkeypatch, mock_owner):
    """Checks that None arguments are replaced by fix_noname_parameter_value result."""
    FIXED_VALUES.clear()
    monkeypatch.setattr("wrappers.smart_locator.fix_noname_parameter_value", lambda *a, **k: ("param", "fixed"))
    sl = SmartLocator(mock_owner, "#sel")
    args, kwargs = sl._validate_arguments((None,), {})
    assert args[0] == "replaced:fixed"
    assert sl.cache_key in FIXED_VALUES
    assert FIXED_VALUES[sl.cache_key][1] == "fixed"


def test_validate_arguments_replaces_strings(mock_owner):
    """Ensures string args get placeholder substitution."""
    FIXED_VALUES.clear()
    sl = SmartLocator(mock_owner, "#sel")
    args, kwargs = sl._validate_arguments(("original",), {})
    assert args[0] == "replaced:original"


def test_fix_locator_updates_cache(monkeypatch, mock_owner):
    """Checks that _fix_locator updates FIXED_SELECTORS and returns a Locator."""
    FIXED_SELECTORS.clear()
    monkeypatch.setattr("wrappers.smart_locator.handle_missing_locator", lambda *a, **k: "#new")
    monkeypatch.setattr("wrappers.smart_locator.update_source_file", lambda *a, **k: None)
    mock_owner.page.locator.return_value = Mock(name="new_locator")

    sl = SmartLocator(mock_owner, "#old")
    new_locator = sl._fix_locator()
    assert FIXED_SELECTORS[sl.cache_key] == "#new"
    assert new_locator is mock_owner.page.locator.return_value


def test_handle_error_when_no_elements(monkeypatch, mock_owner):
    """Simulates _handle_error flow when locator count == 0 (broken selector)."""
    FIXED_SELECTORS.clear()
    mock_owner.page.locator.return_value.count.return_value = 0
    monkeypatch.setattr("wrappers.smart_locator.handle_missing_locator", lambda *a, **k: "#fixed_sel")
    monkeypatch.setattr("wrappers.smart_locator.update_source_file", lambda *a, **k: None)

    sl = SmartLocator(mock_owner, "#bad")
    new_locator, args, kwargs = sl._handle_error(("abc",), {})
    assert isinstance(new_locator, Mock)
    assert new_locator is mock_owner.page.locator.return_value


def test_handle_error_with_existing_elements(monkeypatch, mock_owner):
    """Simulates _handle_error when elements exist but parameters need fixing."""
    FIXED_VALUES.clear()
    mock_owner.page.locator.return_value.count.return_value = 1
    monkeypatch.setattr("wrappers.smart_locator.fix_noname_parameter_value", lambda *a, **k: ("param", "fixed_val"))

    sl = SmartLocator(mock_owner, "#input")
    new_locator, args, kwargs = sl._handle_error(("bad_value",), {})
    assert args[0].startswith("replaced:")
    assert isinstance(new_locator, Mock)
    assert sl.cache_key in FIXED_VALUES


def test_str_representation(monkeypatch, mock_owner):
    """Validates __str__ formatting with fake get_keyword method."""
    def fake_getattr(self, name):
        if name == "get_keyword":
            return lambda: "USER"
        return Mock()
    monkeypatch.setattr("wrappers.smart_locator.SmartLocator.__getattr__", fake_getattr)

    sl = SmartLocator(mock_owner, "#KEYWORD#")
    result = str(sl)
    assert "SmartLocator" in result
    assert "selector" in result

import pytest
from unittest.mock import Mock
from wrappers.smart_page import (
    SmartPage,
    FIXED_PAGE_PARAMETERS,
    FIXED_KEYWORDS,
    FIXED_PLACEHOLDER_NAMES,
    FIXED_PLACEHOLDER_VALUES,
    FIXED_PAGE_SELECTORS,
    PAGE_URL,
    FRAME_NAME,
    FRAME_URL,
)


@pytest.fixture(autouse=True)
def clear_globals():
    """Ensure all global caches are reset for each test."""
    FIXED_PAGE_PARAMETERS.clear()
    FIXED_KEYWORDS.clear()
    FIXED_PLACEHOLDER_NAMES.clear()
    FIXED_PLACEHOLDER_VALUES.clear()
    FIXED_PAGE_SELECTORS.clear()
    yield
    FIXED_PAGE_PARAMETERS.clear()
    FIXED_KEYWORDS.clear()
    FIXED_PLACEHOLDER_NAMES.clear()
    FIXED_PLACEHOLDER_VALUES.clear()
    FIXED_PAGE_SELECTORS.clear()


@pytest.fixture
def mock_page():
    """Mock a Playwright Page with standard methods."""
    page = Mock()
    page.goto = Mock(return_value="navigated")
    page.frame = Mock(return_value="frame_obj")
    page.reload = Mock(return_value="reloaded")
    return page


@pytest.fixture
def mock_placeholder(monkeypatch):
    """Mock PlaceholderManager globally."""
    pm = Mock()
    pm.replace_placeholders_with_values.side_effect = lambda v: f"replaced:{v}"
    monkeypatch.setattr("wrappers.smart_page.PlaceholderManager", lambda c: pm)
    return pm


def make_page(mock_page, mock_placeholder):
    """Helper: create SmartPage with record_mode enabled."""
    return SmartPage(mock_page, {"record_mode": True})


# ---------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------

def test_init_sets_fields(mock_page, mock_placeholder):
    sp = make_page(mock_page, mock_placeholder)
    assert sp.page == mock_page
    assert sp.config["record_mode"]
    assert sp.placeholder_manager == mock_placeholder
    assert "SmartPage" in sp.cache_key


# ---------------------------------------------------------------------
# Placeholder management
# ---------------------------------------------------------------------

def test_add_placeholder_with_name_and_value(mock_page, mock_placeholder):
    sp = make_page(mock_page, mock_placeholder)
    sp.add_placeholder("user", "john")
    mock_placeholder.add_placeholder.assert_called_once_with("user", "john")


def test_add_placeholder_triggers_fix(monkeypatch, mock_page, mock_placeholder):
    monkeypatch.setattr("wrappers.smart_page.fix_noname_parameter_value",
                        lambda *a, **k: ("placeholder", "fixed"))
    sp = make_page(mock_page, mock_placeholder)
    sp.add_placeholder("", "")
    mock_placeholder.add_placeholder.assert_called_once_with("fixed", "fixed")


def test_remove_placeholder(mock_page, mock_placeholder):
    sp = make_page(mock_page, mock_placeholder)
    sp.remove_placeholder("token")
    mock_placeholder.remove_placeholder.assert_called_once_with("token")


# ---------------------------------------------------------------------
# Keyword management
# ---------------------------------------------------------------------

def test_set_and_get_keyword(monkeypatch, mock_page, mock_placeholder):
    monkeypatch.setattr("wrappers.smart_page.fix_noname_parameter_value",
                        lambda *a, **k: ("kw", "fixed_keyword"))
    sp = make_page(mock_page, mock_placeholder)
    sp.set_keyword(None)
    assert FIXED_KEYWORDS
    assert sp.get_keyword() == "fixed_keyword"
    sp.clear_keyword()
    assert sp.keyword is None


# ---------------------------------------------------------------------
# Placeholder validation
# ---------------------------------------------------------------------

def test_validate_placeholder_name(monkeypatch, mock_page, mock_placeholder):
    monkeypatch.setattr("wrappers.smart_page.fix_noname_parameter_value",
                        lambda *a, **k: ("phname", "fixed_name"))
    sp = make_page(mock_page, mock_placeholder)
    result = sp._validate_placeholder_name("")
    assert result == "fixed_name"
    assert FIXED_PLACEHOLDER_NAMES


def test_validate_placeholder_value(monkeypatch, mock_page, mock_placeholder):
    monkeypatch.setattr("wrappers.smart_page.fix_noname_parameter_value",
                        lambda *a, **k: ("phval", "fixed_val"))
    sp = make_page(mock_page, mock_placeholder)
    result = sp._validate_placeholder_value("")
    assert result == "fixed_val"
    assert FIXED_PLACEHOLDER_VALUES


# ---------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------

def test_validate_arguments_for_goto(monkeypatch, mock_page, mock_placeholder):
    monkeypatch.setattr("wrappers.smart_page.fix_noname_parameter_value",
                        lambda *a, **k: ("param", "fixed_url"))
    sp = make_page(mock_page, mock_placeholder)
    args, kwargs = sp._validate_arguments("goto", (None,), {})
    assert args[0] == "fixed_url"
    assert FIXED_PAGE_PARAMETERS
    assert PAGE_URL in "page url"


def test_validate_arguments_for_frame(monkeypatch, mock_page, mock_placeholder):
    monkeypatch.setattr("wrappers.smart_page.fix_noname_parameter_value",
                        lambda *a, **k: ("frameparam", "fixed_frame"))
    sp = make_page(mock_page, mock_placeholder)
    args, kwargs = sp._validate_arguments("frame", (None,), {})
    assert args[0] == "fixed_frame"
    assert FIXED_PAGE_PARAMETERS
    assert FRAME_NAME in "frame name"


def test_validate_arguments_for_selector(mock_page, mock_placeholder):
    sp = make_page(mock_page, mock_placeholder)
    args, kwargs = sp._validate_arguments("click", ("#login",), {})
    assert args[0].startswith("replaced:")


# ---------------------------------------------------------------------
# Fix parameter
# ---------------------------------------------------------------------

def test_fix_parameter_for_goto(monkeypatch, mock_page, mock_placeholder):
    monkeypatch.setattr("wrappers.smart_page.fix_noname_parameter_value",
                        lambda *a, **k: ("url", "fixed_url"))
    sp = make_page(mock_page, mock_placeholder)
    val = sp._fix_parameter("goto", "http://example.com")
    assert val == "replaced:fixed_url"
    assert FIXED_PAGE_PARAMETERS


def test_fix_parameter_for_frame_url(monkeypatch, mock_page, mock_placeholder):
    monkeypatch.setattr("wrappers.smart_page.fix_noname_parameter_value",
                        lambda *a, **k: ("frameurl", "fixed_url"))
    sp = make_page(mock_page, mock_placeholder)
    val = sp._fix_parameter("frame", "http://frame.com")
    assert val == "replaced:fixed_url"
    assert FRAME_URL in "frame url"


def test_fix_parameter_for_frame_name(monkeypatch, mock_page, mock_placeholder):
    monkeypatch.setattr("wrappers.smart_page.fix_noname_parameter_value",
                        lambda *a, **k: ("framename", "fixed_name"))
    sp = make_page(mock_page, mock_placeholder)
    val = sp._fix_parameter("frame", "frameA")
    assert val == "replaced:fixed_name"
    assert FRAME_NAME in "frame name"


# ---------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------

def test_handle_error_raises_when_no_args(mock_page, mock_placeholder):
    sp = make_page(mock_page, mock_placeholder)
    with pytest.raises(Exception):
        sp._handle_error(Exception("no params"), "goto", (), {})


def test_handle_error_with_goto(monkeypatch, mock_page, mock_placeholder):
    monkeypatch.setattr("wrappers.smart_page.fix_noname_parameter_value",
                        lambda *a, **k: ("url", "fixed_url"))
    sp = make_page(mock_page, mock_placeholder)
    args, kwargs = sp._handle_error(Exception("fail"), "goto", ("broken",), {})
    assert args[0].startswith("replaced:")


# ---------------------------------------------------------------------
# Selector fix
# ---------------------------------------------------------------------

def test_fix_selector(monkeypatch, mock_page, mock_placeholder):
    monkeypatch.setattr("wrappers.smart_page.handle_missing_locator", lambda *a, **k: "#new_sel")
    monkeypatch.setattr("wrappers.smart_page.update_source_file", lambda *a, **k: None)
    sp = make_page(mock_page, mock_placeholder)
    sp.selector = "#old"
    sp.field_name = "btn"
    result = sp._fix_selector()
    assert result == "#new_sel"
    assert FIXED_PAGE_SELECTORS


# ---------------------------------------------------------------------
# Proxy / getattr
# ---------------------------------------------------------------------

def test_getattr_invokes_page_method_success(mock_page, mock_placeholder):
    sp = make_page(mock_page, mock_placeholder)
    result = sp.goto("http://example.com")
    assert result == "navigated"
    mock_page.goto.assert_called_once()


def test_getattr_handles_exception(monkeypatch, mock_page, mock_placeholder):
    # mock retryable behavior
    call_counter = {"count": 0}

    def patched_goto(url):
        if call_counter["count"] == 0:
            call_counter["count"] += 1
            raise Exception("Bad URL")
        return f"ok:{url}"

    mock_page.goto = patched_goto
    monkeypatch.setattr("wrappers.smart_page.fix_noname_parameter_value",
                        lambda *a, **k: ("url", "fixed_url"))
    mock_placeholder.replace_placeholders_with_values.side_effect = lambda v: v

    sp = make_page(mock_page, mock_placeholder)
    result = sp.goto("http://broken.com")
    assert result.startswith("ok:")


# ---------------------------------------------------------------------
# Placeholder replacement (extra coverage)
# ---------------------------------------------------------------------

def test_replace_placeholders_on_args_and_kwargs(mock_page, mock_placeholder):
    sp = make_page(mock_page, mock_placeholder)
    args, kwargs = sp._replace_placeholders(("val1",), {"x": "val2"})
    assert args[0] == "replaced:val1"
    assert kwargs["x"] == "replaced:val2"


# ---------------------------------------------------------------------
# String representation
# ---------------------------------------------------------------------

def test_str_and_repr(mock_page, mock_placeholder):
    sp = make_page(mock_page, mock_placeholder)
    s = str(sp)
    assert "SmartPage" in s
    assert s == repr(sp)

import pytest
from unittest.mock import Mock, patch
from wrappers.smart_expect import SmartExpect, expect, FIXED_EXPECTS
from wrappers.smart_locator import SmartLocator


# ---------------------------------------------------------------------
# Global fixtures
# ---------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_global_state():
    """Ensure FIXED_EXPECTS is clean between tests."""
    FIXED_EXPECTS.clear()
    yield
    FIXED_EXPECTS.clear()


@pytest.fixture(autouse=True)
def patch_pw_expect(monkeypatch):
    """Patch playwright.expect to avoid real calls."""
    fake_expect_instance = Mock(name="pw_expect_instance")
    monkeypatch.setattr("wrappers.smart_expect.pw_expect", lambda obj: fake_expect_instance)
    return fake_expect_instance


@pytest.fixture(autouse=True)
def patch_playwright_classes(monkeypatch):
    """Mock Playwright classes so isinstance() passes."""
    Locator = type("Locator", (), {})  # dummy type
    Page = type("Page", (), {})
    APIResponse = type("APIResponse", (), {})
    monkeypatch.setattr("wrappers.smart_expect.Locator", Locator)
    monkeypatch.setattr("wrappers.smart_expect.Page", Page)
    monkeypatch.setattr("wrappers.smart_expect.APIResponse", APIResponse)
    return Locator, Page, APIResponse


@pytest.fixture
def mock_smart_locator():
    sl = Mock(spec=SmartLocator)
    sl.page = Mock()
    sl.config = {"record_mode": True}
    sl.cache_key = "MyPage.field"
    sl.placeholder_manager = Mock()
    sl.placeholder_manager.replace_placeholders_with_values.side_effect = lambda x: f"replaced:{x}"
    sl.selector = "#input"
    sl._fix_locator.return_value = Mock(name="fixed_locator")
    sl.locator = Mock(name="mock_locator")
    return sl


# ---------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------

def test_init_with_smart_locator(mock_smart_locator, patch_pw_expect):
    se = SmartExpect(mock_smart_locator)
    assert se._smart_locator == mock_smart_locator
    assert se.page == mock_smart_locator.page
    assert se._inner == patch_pw_expect
    assert se.cache_key == mock_smart_locator.cache_key


def test_init_with_locator(patch_pw_expect, patch_playwright_classes):
    Locator, _, _ = patch_playwright_classes
    fake_locator = Locator()
    fake_locator.page = Mock()
    se = SmartExpect(fake_locator)
    assert se.page == fake_locator.page
    assert se._inner == patch_pw_expect


def test_init_with_page(patch_pw_expect, patch_playwright_classes):
    _, Page, _ = patch_playwright_classes
    fake_page = Page()
    se = SmartExpect(fake_page)
    assert se.page == fake_page
    assert se._inner == patch_pw_expect


def test_init_with_api_response(patch_pw_expect, patch_playwright_classes):
    _, _, APIResponse = patch_playwright_classes
    fake_resp = APIResponse()
    se = SmartExpect(fake_resp)
    assert se.page is None
    assert se._inner == patch_pw_expect


def test_init_invalid_type_raises():
    with pytest.raises(ValueError):
        SmartExpect(123)


# ---------------------------------------------------------------------
# _validate_arguments tests
# ---------------------------------------------------------------------

def test_validate_arguments_replaces_none(monkeypatch, mock_smart_locator):
    monkeypatch.setattr(
        "wrappers.smart_expect.fix_noname_parameter_value",
        lambda *a, **k: ("expected", "fixed_val"),
    )
    se = SmartExpect(mock_smart_locator)
    args, kwargs = se._validate_arguments((None,), {})
    assert args[0] == "replaced:fixed_val"
    assert FIXED_EXPECTS["MyPage.field"][1] == "fixed_val"


def test_validate_arguments_reuses_cache(mock_smart_locator):
    FIXED_EXPECTS["MyPage.field"] = ("expected", "cached_value")
    se = SmartExpect(mock_smart_locator)
    args, kwargs = se._validate_arguments((None,), {})
    assert args[0] == "replaced:cached_value"


def test_validate_arguments_replaces_string(mock_smart_locator):
    se = SmartExpect(mock_smart_locator)
    args, kwargs = se._validate_arguments(("hello",), {})
    assert args[0] == "replaced:hello"


# ---------------------------------------------------------------------
# _handle_error tests
# ---------------------------------------------------------------------

def test_handle_error_locator_not_found(monkeypatch, mock_smart_locator, patch_pw_expect):
    mock_smart_locator.page.locator.return_value.count.return_value = 0
    se = SmartExpect(mock_smart_locator)
    target = Mock()
    err = Exception("Timeout error")
    new_target, args, kwargs = se._handle_error("to_have_text", target, ("abc",), {}, err)
    assert callable(new_target)
    assert se._inner == patch_pw_expect
    assert new_target == getattr(patch_pw_expect, "to_have_text")


def test_handle_error_locator_expected_value(monkeypatch, mock_smart_locator):
    mock_smart_locator.page.locator.return_value.count.return_value = 1
    monkeypatch.setattr(
        "wrappers.smart_expect.fix_noname_parameter_value",
        lambda *a, **k: ("expected", "fixed_value"),
    )
    se = SmartExpect(mock_smart_locator)
    err = Exception("Locator expected to have text 'wrong'")
    new_target, args, kwargs = se._handle_error("to_have_text", Mock(), ("bad",), {}, err)
    assert args[0] == "replaced:fixed_value"
    assert FIXED_EXPECTS["MyPage.field"][1] == "fixed_value"


# ---------------------------------------------------------------------
# __getattr__ tests
# ---------------------------------------------------------------------

def test_getattr_wraps_to_methods(mock_smart_locator):
    se = SmartExpect(mock_smart_locator)
    inner = se._inner
    mock_target = Mock()
    setattr(inner, "to_have_text", mock_target)
    se._validate_arguments = lambda a, k: (a, k)
    wrapper = se.__getattr__("to_have_text")
    assert callable(wrapper)
    wrapper("val")
    mock_target.assert_called_once_with("val")


def test_getattr_handles_exception(mock_smart_locator):
    se = SmartExpect(mock_smart_locator)
    inner = se._inner
    mock_target = Mock(side_effect=Exception("Locator expected"))
    setattr(inner, "to_have_text", mock_target)
    se._handle_error = lambda *a, **k: (Mock(return_value="fixed"), a[2], a[3])
    wrapper = se.__getattr__("to_have_text")
    result = wrapper("v")
    assert result == "fixed"


def test_getattr_non_to_method(mock_smart_locator):
    se = SmartExpect(mock_smart_locator)
    inner = se._inner
    inner.some_func = Mock(return_value="ok")
    result = se.__getattr__("some_func")
    assert result == inner.some_func


# ---------------------------------------------------------------------
# other tests
# ---------------------------------------------------------------------

def test_dir_returns_inner_dir(mock_smart_locator):
    se = SmartExpect(mock_smart_locator)
    result = se.__dir__()
    assert isinstance(result, list)


def test_expect_function_returns_smartexpect(mock_smart_locator):
    obj = expect(mock_smart_locator)
    assert isinstance(obj, SmartExpect)

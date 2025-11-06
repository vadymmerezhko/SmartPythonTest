import pytest
from unittest.mock import Mock, MagicMock, patch
from playwright.sync_api import Locator, Page, APIResponse
from wrappers.smart_locator import SmartLocator
from wrappers.smart_expect import SmartExpectProxy, expect, FIXED_EXPECTS, EXPECTED_TYPE


@pytest.fixture(autouse=True)
def clear_globals():
    FIXED_EXPECTS.clear()
    yield


# -------------------------------
#  Constructor behavior
# -------------------------------

def test_init_with_smart_locator():
    mock_locator = MagicMock(spec=SmartLocator)
    mock_locator.page = Mock()
    mock_locator.locator = Mock()
    mock_locator.cache_key = "key1"
    mock_locator.placeholder_manager = Mock()
    mock_locator.config = {"record_mode": True}

    with patch("wrappers.smart_expect.pw_expect", return_value="inner_expect") as mock_expect:
        proxy = SmartExpectProxy(mock_locator)

    assert proxy.page == mock_locator.page
    assert proxy._smart_locator == mock_locator
    assert proxy.cache_key == "key1"
    assert proxy.placeholder_manager == mock_locator.placeholder_manager
    mock_expect.assert_called_once_with(mock_locator.locator)
    assert proxy._inner == "inner_expect"


def test_init_with_locator():
    mock_locator = MagicMock(spec=Locator)
    mock_locator.page = Mock()

    with patch("wrappers.smart_expect.pw_expect", return_value="inner_expect"):
        proxy = SmartExpectProxy(mock_locator)

    assert proxy.page == mock_locator.page
    assert proxy._smart_locator is None
    assert proxy._inner == "inner_expect"


def test_init_with_page():
    mock_page = MagicMock(spec=Page)

    with patch("wrappers.smart_expect.pw_expect", return_value="inner_expect"):
        proxy = SmartExpectProxy(mock_page)

    assert proxy.page == mock_page
    assert proxy._inner == "inner_expect"


def test_init_with_apiresponse():
    mock_resp = MagicMock(spec=APIResponse)

    with patch("wrappers.smart_expect.pw_expect", return_value="inner_expect"):
        proxy = SmartExpectProxy(mock_resp)

    assert proxy.page is None
    assert proxy._inner == "inner_expect"


def test_init_with_invalid_type():
    with pytest.raises(ValueError):
        SmartExpectProxy(123)


# -------------------------------
#  validate_arguments()
# -------------------------------

@patch("wrappers.smart_expect.fix_noname_parameter_value", return_value=("fixed", "fixed_value"))
def test_validate_arguments_record_mode_with_none(mock_fix):
    smart_locator = Mock()
    smart_locator.config = {"record_mode": True}
    smart_locator.placeholder_manager = Mock()
    smart_locator.placeholder_manager.replace_placeholders_with_values = lambda x: x
    proxy = SmartExpectProxy.__new__(SmartExpectProxy)
    proxy._smart_locator = smart_locator
    proxy.placeholder_manager = smart_locator.placeholder_manager
    proxy.page = Mock()
    proxy.cache_key = "cache1"

    args, kwargs = proxy.validate_arguments((None,), {})

    assert args[0] == "fixed_value"
    assert "cache1" in FIXED_EXPECTS
    mock_fix.assert_called_once_with(EXPECTED_TYPE, proxy.page, 0, "None", proxy.placeholder_manager)


def test_validate_arguments_replaces_placeholder():
    smart_locator = Mock()
    smart_locator.config = {"record_mode": False}
    smart_locator.placeholder_manager = Mock()
    smart_locator.placeholder_manager.replace_placeholders_with_values = lambda v: v.replace("#A#", "OK")

    proxy = SmartExpectProxy.__new__(SmartExpectProxy)
    proxy._smart_locator = smart_locator
    proxy.placeholder_manager = smart_locator.placeholder_manager
    proxy.page = Mock()
    proxy.cache_key = "cache2"

    args, kwargs = proxy.validate_arguments(("#A#",), {})
    assert args[0] == "OK"


# -------------------------------
#  __getattr__() and wrapper()
# -------------------------------

def test_getattr_returns_non_callable():
    proxy = SmartExpectProxy.__new__(SmartExpectProxy)
    proxy._inner = Mock()
    proxy._inner.some_attr = "abc"
    result = proxy.__getattr__("some_attr")
    assert result == "abc"


def test_getattr_wraps_to_method_and_calls_target():
    inner = Mock()
    inner.to_have_text = Mock(return_value="ok")

    proxy = SmartExpectProxy.__new__(SmartExpectProxy)
    proxy._inner = inner
    proxy._smart_locator = Mock()
    proxy._smart_locator.config = {"record_mode": False}

    result = proxy.__getattr__("to_have_text")("value1")
    assert result == "ok"


@patch("wrappers.smart_expect.normalize_args", return_value=(("fixed",), {}))
@patch("wrappers.smart_expect.fix_noname_parameter_value", return_value=("fixed", "new_val"))
def test_getattr_retries_with_smart_locator(mock_fix, mock_norm):
    inner = Mock()
    inner.to_have_text = Mock(return_value="result")
    placeholder_mgr = Mock()
    placeholder_mgr.replace_placeholders_with_values = lambda x: x

    smart_locator = Mock()
    smart_locator.page = Mock()
    smart_locator.placeholder_manager = placeholder_mgr
    smart_locator.config = {"record_mode": True}
    smart_locator.cache_key = "k"
    smart_locator.fix_locator = Mock(return_value="fixed_locator")
    smart_locator.selector = "#a"

    with patch("wrappers.smart_expect.pw_expect", return_value=inner):
        proxy = SmartExpectProxy.__new__(SmartExpectProxy)
        proxy._inner = inner
        proxy._smart_locator = smart_locator
        proxy.page = smart_locator.page
        proxy.cache_key = smart_locator.cache_key
        proxy.placeholder_manager = placeholder_mgr

        wrapped = proxy.__getattr__("to_have_text")
        assert callable(wrapped)
        result = wrapped("expected_value")
        assert result == "result"


# -------------------------------
#  expect() function
# -------------------------------

def test_expect_returns_proxy():
    obj = Mock()
    with patch("wrappers.smart_expect.SmartExpectProxy", return_value="proxy_mock") as mock_proxy:
        result = expect(obj)
    assert result == "proxy_mock"
    mock_proxy.assert_called_once_with(obj)

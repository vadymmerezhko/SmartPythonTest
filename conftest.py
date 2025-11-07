import json
import pytest
from enums.update_type import UpdateType
from playwright.sync_api import sync_playwright


# Safe helper (avoids circular import)
from helpers.test_context import set_current_param_row, get_current_param_row

# Global maps from wrappers
from wrappers.smart_locator import FIXED_SELECTORS, FIXED_VALUES
from wrappers.smart_page import (FIXED_KEYWORDS, FIXED_PAGE_PARAMETERS,
                                 FIXED_PLACEHOLDER_NAMES, FIXED_PLACEHOLDER_VALUES)
from wrappers.smart_expect import FIXED_EXPECTS


# ---------------------------------------------------------------------------
# Load configuration
# ---------------------------------------------------------------------------
with open("config.json", encoding="utf-8") as f:
    CONFIG = json.load(f)


# ---------------------------------------------------------------------------
# Record current parametrize row
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def record_param_row(request):
    """Store current pytest parametrize row index in helpers.test_context."""
    if hasattr(request.node, "callspec"):
        indices = getattr(request.node.callspec, "indices", None)
        if indices:
            set_current_param_row(list(indices.values())[0])
        else:
            set_current_param_row(-1)
    else:
        set_current_param_row(-1)

    yield
    set_current_param_row(-1)


# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------
def pytest_addoption(parser):
    parser.addoption(
        "--record_mode",
        action="store",
        choices=["true", "false"],
        help="Override record_mode from config.json",
    )
    parser.addoption(
        "--username",
        "--test_placeholder",
        action="store",
        help="Custom username override",
    )


# ---------------------------------------------------------------------------
# Config fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def config(pytestconfig):
    cfg = CONFIG.copy()

    browser = pytestconfig.getoption("browser")
    headed = pytestconfig.getoption("headed")
    if browser:
        cfg["browser"] = browser
    cfg["headless"] = not bool(headed)

    record_mode = pytestconfig.getoption("record_mode")
    if record_mode is not None:
        cfg["record_mode"] = record_mode.lower() == "true"
    else:
        cfg["record_mode"] = bool(cfg.get("record_mode", False))

    username = pytestconfig.getoption("username")
    if username:
        cfg["username"] = username

    return cfg

# ---------------------------------------------------------------------------
# Clear FIXED_* maps every test function run
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_smart_globals():
    # Reset global map items for every data provider test run

    for key, value in list(FIXED_PAGE_PARAMETERS.items()):
        if value[0] == UpdateType.DATA_PROVIDER:
            del FIXED_PAGE_PARAMETERS[key]

    for key, value in list(FIXED_VALUES.items()):
        if value[0] == UpdateType.DATA_PROVIDER:
            del FIXED_VALUES[key]

    for key, value in list(FIXED_KEYWORDS.items()):
        if value[0] == UpdateType.DATA_PROVIDER:
            del FIXED_KEYWORDS[key]

    for key, value in list(FIXED_EXPECTS.items()):
        if value[0] == UpdateType.DATA_PROVIDER:
            del FIXED_EXPECTS[key]

    for key, value in list(FIXED_PLACEHOLDER_NAMES.items()):
        if value[0] == UpdateType.DATA_PROVIDER:
            del FIXED_PLACEHOLDER_NAMES[key]

    for key, value in list(FIXED_PLACEHOLDER_VALUES.items()):
        if value[0] == UpdateType.DATA_PROVIDER:
            del FIXED_PLACEHOLDER_VALUES[key]

    yield

# ---------------------------------------------------------------------------
# Final cleanup after the entire session
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def reset_fixed_selectors_after_session():
    yield
    FIXED_SELECTORS.clear()
    FIXED_VALUES.clear()
    FIXED_KEYWORDS.clear()
    FIXED_EXPECTS.clear()


# ---------------------------------------------------------------------------
# Playwright fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def playwright_instance():
    """Provide a shared Playwright instance."""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance, config):
    """Launch a browser based on config."""
    browser_name = config.get("browser", "chromium")
    headless = config.get("headless", True)
    browser = getattr(playwright_instance, browser_name).launch(headless=headless)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser, config):
    """New browser context per test."""
    context = browser.new_context()
    context.set_default_timeout(config.get("timeout", 30000))
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context, config):
    """New page per test."""
    page = context.new_page()
    page.set_default_timeout(config.get("timeout", 30000))
    yield page
    page.close()

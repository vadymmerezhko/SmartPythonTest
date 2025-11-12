import datetime
import json
from pathlib import Path
import pytest
import time
import re
from enums.update_type import UpdateType
from playwright.sync_api import sync_playwright
from helpers.test_context import set_current_param_row, get_current_param_row

# Global maps from wrappers
from wrappers.smart_locator import FIXED_SELECTORS, FIXED_VALUES
from wrappers.smart_page import (FIXED_KEYWORDS, FIXED_PAGE_PARAMETERS,
                                 FIXED_PLACEHOLDER_NAMES, FIXED_PLACEHOLDER_VALUES)
from wrappers.smart_expect import FIXED_EXPECTS


REPORT_DIR = Path.cwd() / "reports"
REPORT_FILE = REPORT_DIR / "report.html"


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
        "--highlight",
        action="store",
        choices=["true", "false"],
        help="Highlight elements during tests",
    )

    parser.addoption(
        "--screenshot_on_error",
        action="store",
        default="true",
        help="Capture screenshot on test failure",
    )

    parser.addoption(
        "--step_delay",
        action="store",
        type=int,
        help="Delay (in ms) between steps",
    )

    parser.addoption(
        "--username",
        action="store",
        help="Custom username override",
    )

    parser.addoption(
        "--test_placeholder",
        action="store",
        help="Override test placeholder text",
    )


# ---------------------------------------------------------------------------
# Config fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def config(pytestconfig):
    cfg = CONFIG.copy()

    # Browser and headless
    browser = pytestconfig.getoption("browser")
    headed = pytestconfig.getoption("headed")
    if browser:
        cfg["browser"] = browser
    cfg["headless"] = not bool(headed)

    # Record mode
    record_mode = pytestconfig.getoption("record_mode")
    if record_mode is not None:
        cfg["record_mode"] = record_mode.lower() == "true"
    else:
        cfg["record_mode"] = bool(cfg.get("record_mode", False))

    # Username
    username = pytestconfig.getoption("username")
    if username:
        cfg["username"] = username

    # Highlight mode
    highlight = pytestconfig.getoption("highlight")
    if highlight is not None:
        cfg["highlight"] = highlight.lower() == "true"
    else:
        cfg["highlight"] = bool(cfg.get("highlight", False))

    # Screenshot on error
    screenshot_on_error = pytestconfig.getoption("screenshot_on_error")
    if screenshot_on_error is not None:
        cfg["screenshot_on_error"] = screenshot_on_error.lower() == "true"
    else:
        cfg["screenshot_on_error"] = bool(cfg.get("screenshot_on_error", False))

    # Step delay
    step_delay = pytestconfig.getoption("step_delay")
    if step_delay is not None:
        try:
            cfg["step_delay"] = float(step_delay)
        except ValueError:
            cfg["step_delay"] = 0.0
    else:
        cfg["step_delay"] = float(cfg.get("step_delay", 0.0))

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


def pytest_configure(config):
    """Make sure reports/ exists and direct pytest-html there."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    config.option.htmlpath = str(REPORT_FILE)
    print(f"[INFO] HTML report → {REPORT_FILE}")


def pytest_sessionstart(session):
    """Delete old report & screenshots before the session begins."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    for f in REPORT_DIR.glob("*"):
        try:
            f.unlink()
        except Exception as e:
            print(f"[WARN] Could not remove {f}: {e}")


def safe_filename(name: str) -> str:
    """
    Convert any string (like test names or parameterized values)
    into a filesystem-safe filename.
    Keeps letters, digits, underscore, dash, and dot only.
    """
    # Replace all invalid filename chars with '_'
    name = re.sub(r'[<>:"/\\|?*\s,=#@!%^&;{}()+]+', '_', name)
    # Collapse consecutive underscores
    name = re.sub(r'_+', '_', name)
    # Trim leading/trailing underscores or dots
    name = name.strip('._')
    return name[:150]  # limit length to avoid OS path length issues


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture a Playwright screenshot and attach it to the HTML report."""
    outcome = yield
    rep = outcome.get_result()

    # Run only when the test itself failed
    if rep.when != "call" or not rep.failed:
        return

    try:
        # Get config option
        opt_value = item.config.getoption("screenshot_on_error") or "true"
        screenshot_enabled = str(opt_value).strip().lower() == "true"

        if not screenshot_enabled:
            return

        # Import safely inside hook (pytest loads this very early)
        from playwright.sync_api import Page

        page = item.funcargs.get("page", None)
        if not page or not isinstance(page, Page):
            return

        from datetime import datetime

        # Build unique name: {test-name}-yyyy-MM-dd-hh-mm-ss-sss.png
        ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")[:-3]
        safe_test_name = safe_filename(item.name)
        screenshot_name = f"{safe_test_name}-{ts}.png"
        screenshot_path = REPORT_DIR / screenshot_name

        # Give browser time to render any failure overlay
        time.sleep(0.2)

        # Take screenshot
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"[INFO] Screenshot saved → {screenshot_path}")

        # Attach to pytest-html report
        html = item.config.pluginmanager.getplugin("html")
        if html:
            rel_path = screenshot_path.name
            link_html = f'<a href="{rel_path}" target="_blank">Open Screenshot</a>'
            rep.extra = getattr(rep, "extra", [])
            rep.extra.append(html.extras.html(link_html))
            rep.extra.append(html.extras.image(rel_path))

    except Exception as e:
        print(f"[WARN] Screenshot capture failed: {e}")

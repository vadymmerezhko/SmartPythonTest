import json
import pytest
from playwright.sync_api import sync_playwright

# Load defaults from config.json
with open("config.json") as f:
    CONFIG = json.load(f)


def pytest_addoption(parser):
    parser.addoption(
        "--record_mode",
        action="store",
        choices=["true", "false"],
        help="Override record_mode from config.json"
    )
    parser.addoption(
        "--username",
        action="store",
        help="Custom username override"
    )


@pytest.fixture(scope="session")
def config(pytestconfig):
    cfg = CONFIG.copy()

    # Built-in pytest-playwright options
    browser = pytestconfig.getoption("browser")
    headed = pytestconfig.getoption("headed")

    if browser:
        cfg["browser"] = browser

    # pytest-playwright uses --headed (default False)
    cfg["headless"] = not headed

    # Custom: record_mode override
    record_mode = pytestconfig.getoption("record_mode")
    if record_mode is not None:
        cfg["record_mode"] = record_mode.lower() == "true"

    # Custom: username override
    username = pytestconfig.getoption("username")
    if username:
        cfg["username"] = username

    return cfg


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance, config):
    # Use browser from config, default to chromium
    browser_name = config.get("browser", "chromium")
    headless = config.get("headless", True)
    browser = getattr(playwright_instance, browser_name).launch(headless=headless)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser, config):
    context = browser.new_context()
    context.set_default_timeout(config.get("timeout", 30000))  # default 30s
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context, config):
    page = context.new_page()
    page.set_default_timeout(config.get("timeout", 30000))  # ensure page-level
    yield page
    page.close()

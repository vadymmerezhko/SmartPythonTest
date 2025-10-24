import json
import pytest
from playwright.sync_api import sync_playwright

# Load defaults from config.json
with open("config.json") as f:
    CONFIG = json.load(f)


@pytest.fixture(scope="session")
def config(pytestconfig):
    cfg = CONFIG.copy()

    # Built-in pytest-playwright options
    base_url = pytestconfig.getoption("base_url")
    browser = pytestconfig.getoption("browser")
    headed = pytestconfig.getoption("headed")

    if base_url:
        cfg["demo_base_url"] = base_url
    if browser:
        cfg["browser"] = browser

    # pytest-playwright uses --headed (default False)
    cfg["headless"] = not headed

    # Custom options (only if you add them with pytest_addoption)
    username = getattr(pytestconfig.option, "username", None)
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

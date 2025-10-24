import pytest
from utils import web_utils


@pytest.mark.skipif(not web_utils.GUI_AVAILABLE, reason="Requires GUI (not available in CI)")
def test_get_hovered_element_locator(page):
    page.goto("https://www.saucedemo.com/")
    # Hover over username input
    page.locator("#user-name").hover()
    locator = web_utils.get_hovered_element_locator(page)
    assert locator.count() == 1
    assert locator.evaluate("el => el.id") == "user-name"


def test_highlight_and_reset(page):
    page.goto("https://www.saucedemo.com/")
    locator = page.locator("#login-button")

    orig_style = web_utils.highlight_element(locator)
    style_after = locator.get_attribute("style")
    assert "border: 2px solid red" in style_after

    web_utils.reset_element_style(locator, orig_style)
    restored = locator.get_attribute("style")
    assert restored == orig_style


def test_get_unique_css_selector(page):
    page.goto("https://www.saucedemo.com/")
    locator = page.locator("#password")
    selector = web_utils.get_unique_css_selector(locator)
    assert selector == "#password"


def test_compare_locators_geometry(page):
    page.goto("https://www.saucedemo.com/")
    locator1 = page.locator("#user-name")
    locator2 = page.locator("#user-name")
    locator3 = page.locator("#login-button")

    assert web_utils.compare_locators_geometry(locator1, locator2)
    assert not web_utils.compare_locators_geometry(locator1, locator3)

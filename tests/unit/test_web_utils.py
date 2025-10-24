import pytest
from utils.web_utils import (get_hovered_element_locator, highlight_element,
                             reset_element_style, get_unique_css_selector,
                             compare_locators_geometry)


class DummyLocator:
    def __init__(self, selector):
        self.selector = selector

class DummyPage:
    def __init__(self, selector_to_return=None):
        self._selector_to_return = selector_to_return
        self.evaluate_called = False

    def evaluate(self, script):
        self.evaluate_called = True
        return self._selector_to_return

    def locator(self, selector):
        return DummyLocator(selector)


def test_get_hovered_element_success():
    page = DummyPage("input#user-name")
    locator = get_hovered_element_locator(page)

    assert isinstance(locator, DummyLocator)
    assert locator.selector == "input#user-name"
    assert page.evaluate_called


def test_get_hovered_element_none():
    page = DummyPage(None)
    with pytest.raises(RuntimeError, match="No element is currently hovered"):
        get_hovered_element_locator(page)


@pytest.mark.parametrize("selector", [
    "#user-name",   # username field
    "#password",    # password field
    "#login-button" # login button
])
def test_highlight_and_reset(page, selector):
    # Open SauceDemo login page
    page.goto("https://www.saucedemo.com/")

    # Get element locator
    locator = page.locator(selector)

    # Save original style
    orig_style = locator.get_attribute("style")

    # Highlight element
    saved_style = highlight_element(locator)

    # Check element now has red border
    style_after = locator.get_attribute("style")
    assert "border: 2px solid red" in style_after

    # Saved style should equal original style
    assert saved_style == orig_style

    # Reset element style
    reset_element_style(locator, saved_style)

    # Check style restored
    restored_style = locator.get_attribute("style")
    assert restored_style == orig_style


@pytest.mark.parametrize("selector", [
    "#user-name",    # username field
    "#password",     # password field
    "#login-button", # login button
])
def test_get_unique_css_selector(page, selector):
    # Navigate to SauceDemo login page
    page.goto("https://www.saucedemo.com/")

    # Get element locator from original selector
    element = page.locator(selector).first
    assert element.count() == 1, f"Original selector {selector} not unique"

    # Generate unique selector
    unique_sel = get_unique_css_selector(element)
    assert unique_sel is not None, f"Could not generate unique selector for {selector}"

    # Validate new selector points to the same element
    new_locator = page.locator(unique_sel).first
    assert new_locator.count() == 1, f"Generated selector {unique_sel} is not unique"

    # Compare some attribute (id or tagName) to confirm same element
    orig_id = element.evaluate("el => el.id")
    new_id = new_locator.evaluate("el => el.id")
    assert orig_id == new_id, f"Selector mismatch: expected id={orig_id}, got {new_id}"


def test_compare_same_element(page):
    page.goto("https://www.saucedemo.com/")

    loc1 = page.locator("#user-name")
    loc2 = page.locator("input[name='user-name']")

    assert compare_locators_geometry(loc1, loc2) is True


def test_compare_different_elements(page):
    page.goto("https://www.saucedemo.com/")

    loc1 = page.locator("#user-name")
    loc2 = page.locator("#password")

    assert compare_locators_geometry(loc1, loc2) is False


def test_invisible_element(page):
    page.set_content("<div id='visible'>Visible</div><div id='hidden' style='display:none'>Hidden</div>")

    loc1 = page.locator("#visible")
    loc2 = page.locator("#hidden")

    with pytest.raises(ValueError):
        compare_locators_geometry(loc1, loc2)

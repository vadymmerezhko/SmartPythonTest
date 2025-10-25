import pytest
from unittest.mock import MagicMock
from utils.web_utils import (compare_locators_geometry,
                             get_simple_css_selector,
                             get_complex_css_selector,
                            get_hovered_element_locator,
                             highlight_element,
                             reset_element_style)


def test_get_hovered_element_locator(page):
    page.goto("https://www.saucedemo.com/")
    # Hover over username input
    page.locator("#user-name").hover()
    locator = get_hovered_element_locator(page)
    assert locator.count() == 1
    assert locator.evaluate("el => el.id") == "user-name"


def test_highlight_and_reset(page):
    page.goto("https://www.saucedemo.com/")
    locator = page.locator("#login-button")

    orig_style = highlight_element(locator)
    style_after = locator.get_attribute("style")
    assert "border: 2px solid red" in style_after

    reset_element_style(locator, orig_style)
    restored = locator.get_attribute("style")
    assert restored == orig_style


def test_get_simple_css_selector(page):
    page.goto("https://www.saucedemo.com/")
    locator = page.locator("#password")
    selector = get_simple_css_selector(locator)
    assert selector == "#password"


def test_compare_locators_geometry(page):
    page.goto("https://www.saucedemo.com/")
    locator1 = page.locator("#user-name")
    locator2 = page.locator("#user-name")
    locator3 = page.locator("#login-button")

    assert compare_locators_geometry(locator1, locator2)
    assert not compare_locators_geometry(locator1, locator3)


class FakeLocator:
    """Fake Playwright Locator that simulates attributes + DOM uniqueness."""

    def __init__(self, tag, attrs, unique_selectors):
        self._tag = tag
        self._attrs = attrs
        self.page = MagicMock()
        self.page.evaluate = self._page_evaluate
        self._unique_selectors = set(unique_selectors)

    def evaluate(self, script):
        """Simulates locator.evaluate() returning tag + attributes."""
        return {"tag": self._tag, "attrs": self._attrs}

    def _page_evaluate(self, script, selector):
        """Simulates uniqueness check."""
        return selector in self._unique_selectors


def test_returns_none_if_no_element_info():
    locator = MagicMock()
    locator.evaluate.return_value = None
    assert get_complex_css_selector(locator) is None


def test_returns_none_if_less_than_two_attributes():
    locator = FakeLocator("input", {"class": "foo"}, [])
    assert get_complex_css_selector(locator) is None


def test_finds_unique_pair_selector():
    attrs = {"class": "foo", "type": "text", "role": "input"}
    unique = {"input[class='foo'][type='text']"}
    locator = FakeLocator("input", attrs, unique)

    result = get_complex_css_selector(locator)
    assert result == "input[class='foo'][type='text']"


def test_needs_one_attribute_if_tag_not_unique():
    attrs = {"class": "login_logo"}
    unique = {"div[class='login_logo']"}
    locator = FakeLocator("div", attrs, unique)

    result = get_complex_css_selector(locator)
    assert result == "div[class='login_logo']"


def test_needs_three_attributes_if_pairs_not_unique():
    attrs = {"class": "foo", "type": "text", "role": "input"}
    unique = {"input[class='foo'][type='text'][role='input']"}
    locator = FakeLocator("input", attrs, unique)

    result = get_complex_css_selector(locator)
    assert result == "input[class='foo'][type='text'][role='input']"


def test_returns_none_if_no_unique_selector_found():
    attrs = {"class": "foo", "type": "text", "role": "input"}
    unique = set()
    locator = FakeLocator("input", attrs, unique)

    result = get_complex_css_selector(locator)
    assert result is None


def test_unique_tag_selector():
    # Tag <button> alone is unique
    locator = FakeLocator("button", {"class": "btn", "type": "submit"}, unique_selectors={"button"})
    result = get_complex_css_selector(locator)
    assert result == "button"



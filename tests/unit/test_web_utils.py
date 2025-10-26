import pytest
from playwright.sync_api import Page
from unittest.mock import MagicMock
from urllib.parse import urljoin
from utils.web_utils import (compare_locators_geometry,
                             get_simple_css_selector,
                             get_complex_css_selector,
                             get_css_selector_by_parent,
                             get_css_selector_by_sibling,
                             get_xpath_selector_by_text,
                             get_xpath_selector_by_parent_text,
                             get_hovered_element_locator,
                             highlight_element,
                             reset_element_style,
                             xpath_to_css)

LOGIN_URL = "https://www.saucedemo.com/"
USERNAME = "standard_user"
PASSWORD = "secret_sauce"
INVENTORY_PATH = "inventory.html"


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


@pytest.fixture(scope="function")
def login(page, config):
    # navigate to login
    page.goto(LOGIN_URL)
    # login
    page.fill("#user-name", USERNAME)
    page.fill("#password", PASSWORD)
    page.click("#login-button")
    # ensure landing on inventory page
    expected = urljoin(config["demo_base_url"], INVENTORY_PATH)
    assert page.url == expected, f"Expected {expected}, got {page.url}"
    return page

def test_inventory_header(login):
    # once logged in, check header text
    header_locator = login.locator(".header_secondary_container .title")
    assert header_locator.inner_text().strip() == "Products"

def test_cart_icon_present(login):
    cart_icon = login.locator(".shopping_cart_link")
    assert cart_icon.is_visible()


def test_simple_tag_indexed():
    # (//tag)[n] -> tag:nth-of-type(n)
    assert xpath_to_css("(//div)[1]") == "div:nth-of-type(1)"
    assert xpath_to_css("(//span)[3]") == "span:nth-of-type(3)"


def test_tag_with_attribute():
    # //tag[@attr='value'] -> tag[attr='value']
    assert xpath_to_css("//input[@type='text']") == "input[type='text']"
    assert xpath_to_css("//button[@id='login']") == "button[id='login']"


def test_wildcard():
    # //* -> *
    assert xpath_to_css("//*") == "*"


def test_invalid_xpaths_return_none():
    # Not matching any of the simple patterns
    assert xpath_to_css("//div") is None
    assert xpath_to_css("//div[@class=\"foo\"]") is None  # double quotes not supported
    assert xpath_to_css("(//div)[a]") is None             # invalid index
    assert xpath_to_css("") is None
    assert xpath_to_css("random") is None


@pytest.fixture(scope="function")
def logged_in_page(page: Page):
    """Login to saucedemo and return page on inventory.html"""
    page.goto(LOGIN_URL)
    page.fill("#user-name", USERNAME)
    page.fill("#password", PASSWORD)
    page.click("#login-button")
    # ensure we are on inventory page
    expected_url = urljoin(LOGIN_URL, INVENTORY_PATH)
    page.wait_for_url(expected_url)
    return page


def test_cart_icon_selector(logged_in_page: Page):
    locator = logged_in_page.locator("#shopping_cart_container")
    selector = get_css_selector_by_parent(locator)
    assert selector is not None
    # Ensure selector identifies cart container within header
    assert "primary_header" in selector
    assert selector.endswith("> div")


def test_inventory_item_selector(logged_in_page: Page):
    locator = logged_in_page.locator(".inventory_item_name").first
    selector = get_css_selector_by_parent(locator)
    assert selector is not None
    # Ensure it correctly links the unique id of the item name
    assert "#item_4_title_link" in selector
    # Ensure it’s selecting a child inside that parent
    assert selector.startswith("#item_4_title_link")
    assert selector.endswith("> div")


def test_add_to_cart_button_selector(logged_in_page: Page):
    locator = logged_in_page.locator("button.btn_inventory").first
    selector = get_css_selector_by_parent(locator)
    assert selector is not None
    # should end with '> button'
    assert selector.strip().endswith("> button")


def test_price_label_selector(logged_in_page: Page):
    locator = logged_in_page.locator(".inventory_item_price").first
    selector = get_css_selector_by_parent(locator)
    assert selector is not None
    # should end with '> div'
    assert selector.strip().endswith("> div")


def test_price_by_sibling(logged_in_page: Page):
    locator = logged_in_page.locator(".inventory_item_price").first
    selector = get_css_selector_by_sibling(locator)
    print("Price selector:", selector)
    assert selector is None or selector.endswith("+ div")


def test_button_by_price_sibling(logged_in_page: Page):
    locator = logged_in_page.locator("button.btn_inventory").first
    selector = get_css_selector_by_sibling(locator)
    print("Button selector:", selector)
    assert selector is None or selector.endswith("+ button")


def test_cart_icon_by_menu_button_sibling(logged_in_page: Page):
    locator = logged_in_page.locator("#shopping_cart_container")
    selector = get_css_selector_by_sibling(locator)
    print("Cart icon selector:", selector)
    # It may be None if not unique, so don’t force uniqueness
    assert selector is None or "div" in selector


def test_inventory_name_by_image_sibling(logged_in_page: Page):
    locator = logged_in_page.locator(".inventory_item_name").first
    selector = get_css_selector_by_sibling(locator)
    print("Inventory name selector:", selector)
    assert selector is None or selector.endswith("+ a") or selector.endswith("+ div")


def _xpath_count(page: Page, xpath: str) -> int:
    return page.locator(xpath).count()


def _same_element(page: Page, locator, xpath: str) -> bool:
    # Compare bounding boxes to ensure it's the same element
    return compare_locators_geometry(page.locator(xpath), locator)

def test_add_to_cart_button_xpath(logged_in_page: Page):
    loc = logged_in_page.locator("button.btn_inventory").first
    xp = get_xpath_selector_by_text(loc)
    assert xp is not None
    assert _xpath_count(logged_in_page, xp) == 1
    assert _same_element(logged_in_page, loc, xp)

def test_price_xpath(logged_in_page: Page):
    loc = logged_in_page.locator(".inventory_item_price").first
    xp = get_xpath_selector_by_text(loc)
    assert xp is not None
    assert _xpath_count(logged_in_page, xp) == 1
    assert _same_element(logged_in_page, loc, xp)

def test_product_name_xpath(logged_in_page: Page):
    loc = logged_in_page.locator(".inventory_item_name").first
    xp = get_xpath_selector_by_text(loc)
    assert xp is not None
    assert _xpath_count(logged_in_page, xp) == 1
    assert _same_element(logged_in_page, loc, xp)

def test_element_without_text_returns_none(logged_in_page: Page):
    # Cart container has no direct text
    loc = logged_in_page.locator("#shopping_cart_container")
    xp = get_xpath_selector_by_text(loc)
    assert xp is None

def test_inventory_item_name_by_parent_text(logged_in_page: Page):
    locator = logged_in_page.locator(".inventory_item_name").first
    xp = get_xpath_selector_by_parent_text(locator)
    assert xp is not None
    # verify xpath selects same element
    assert _xpath_count(logged_in_page, xp) == 1

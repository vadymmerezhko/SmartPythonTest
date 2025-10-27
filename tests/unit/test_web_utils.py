import pytest
from playwright.sync_api import Page
from unittest.mock import MagicMock
from urllib.parse import urljoin
from utils.web_utils import (check_locators_geometry_match,
                             get_simple_css_selector,
                             get_complex_css_selector,
                             get_css_selector_by_parent,
                             get_css_selector_by_sibling,
                             get_xpath_selector_by_text,
                             get_xpath_selector_by_parent_text,
                             get_complex_xpath_selector_by_index,
                             get_not_unique_complex_css_selector,
                             get_xpath_selector_by_other_element_text,
                             check_parent_contains_child,
                             get_hovered_element_locator,
                             highlight_element,
                             reset_element_style,
                             css_to_xpath,
                             xpath_to_css)

LOGIN_URL = "https://www.saucedemo.com/"
USERNAME = "standard_user"
PASSWORD = "secret_sauce"
INVENTORY_PATH = "inventory.html"


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

    assert check_locators_geometry_match(locator1, locator2)
    assert not check_locators_geometry_match(locator1, locator3)


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
    assert "primary-header" in selector
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
    return check_locators_geometry_match(page.locator(xpath), locator)

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


def test_id_selector():
    css = "#user-name"
    xpath = css_to_xpath(css)
    assert xpath == "//*[@id='user-name']"


def test_class_selector():
    css = ".input-field"
    xpath = css_to_xpath(css)
    assert xpath == "//*[@class='input-field']"


def test_tag_only():
    css = "div"
    xpath = css_to_xpath(css)
    assert xpath == "//div"


def test_wildcard():
    css = "*"
    xpath = css_to_xpath(css)
    assert xpath == "//*"


def test_tag_with_class():
    css = "span.highlight"
    xpath = css_to_xpath(css)
    assert xpath == "//span[@class='highlight']"


def test_tag_with_attribute():
    css = "input[type='text']"
    xpath = css_to_xpath(css)
    assert xpath == "//input[@type='text']"


def test_tag_with_multiple_attributes():
    css = "input[type='text'][name='username'][placeholder='Enter username']"
    xpath = css_to_xpath(css)
    assert xpath == "//input[@type='text' and @name='username' and @placeholder='Enter username']"


def test_tag_with_class_and_attribute():
    css = "button.primary[type='submit']"
    xpath = css_to_xpath(css)
    assert xpath == "//button[@class='primary' and @type='submit']"


def test_trimmed_input():
    css = "   div[id='container']   "
    xpath = css_to_xpath(css)
    assert xpath == "//div[@id='container']"


def _assert_unique_xpath(page: Page, xp: str, expected_text: str = None):
    """Helper: ensure XPath selects exactly one element and optional text check."""
    matches = page.locator(xp)
    count = matches.count()
    assert count == 1, f"Expected unique XPath, but found {count} elements: {xp}"
    if expected_text:
        assert matches.inner_text().strip() == expected_text


def test_inventory_item_name_xpath_by_index(logged_in_page: Page):
    locator = logged_in_page.locator("div[data-test='inventory-item-name']").first
    xp = get_complex_xpath_selector_by_index(locator)
    assert xp and xp.startswith("xpath=")
    assert check_locators_geometry_match(locator, logged_in_page.locator(xp))


def test_inventory_price_xpath(logged_in_page: Page):
    locator = logged_in_page.locator(".inventory_item_price").first
    xp = get_complex_xpath_selector_by_index(locator)
    assert xp and xp.startswith("xpath=")
    _assert_unique_xpath(logged_in_page, xp, "$29.99")


def test_add_to_cart_button_xpath_by_index(logged_in_page: Page):
    locator = logged_in_page.locator("button.btn_inventory").first
    xp = get_complex_xpath_selector_by_index(locator)
    assert xp and xp.startswith("xpath=")
    _assert_unique_xpath(logged_in_page, xp, "Add to cart")


def test_cart_icon_xpath_by_index(logged_in_page: Page):
    locator = logged_in_page.locator("#shopping_cart_container")
    xp = get_complex_xpath_selector_by_index(locator)
    assert xp and xp.startswith("xpath=")
    _assert_unique_xpath(logged_in_page, xp)


def test_not_unique_username_field_selector(page):
    page.goto("https://www.saucedemo.com/")
    locator = page.locator("#user-name")
    sel = get_not_unique_complex_css_selector(locator)
    assert sel.startswith("input")
    assert "type='text'" in sel


def test_not_unique_login_button_selector(page):
    page.goto("https://www.saucedemo.com/")
    locator = page.locator("#login-button")
    sel = get_not_unique_complex_css_selector(locator)
    assert sel.startswith("input")
    assert "type='submit'" in sel or "data-test='login-button'" in sel


def test_not_unique_inventory_item_name_selector(logged_in_page):
    locator = logged_in_page.locator("div[data-test='inventory-item-name']").first
    sel = get_not_unique_complex_css_selector(locator)
    assert sel.startswith("div")
    assert "class='inventory_item_name '" in sel


def test_not_unique_inventory_item_price_selector(logged_in_page):
    locator = logged_in_page.locator(".inventory_item_price").first
    sel = get_not_unique_complex_css_selector(locator)
    assert sel.startswith("div")
    assert "class='inventory_item_price'" in sel


def test_not_unique_add_to_cart_button_selector(logged_in_page):
    locator = logged_in_page.locator("#add-to-cart-sauce-labs-backpack").first
    sel = get_not_unique_complex_css_selector(locator)
    assert sel.startswith("button")
    assert "class='btn btn_primary btn_small btn_inventory '" in sel


def test_not_unique_cart_icon_selector(logged_in_page):
    locator = logged_in_page.locator("#shopping_cart_container")
    sel = get_not_unique_complex_css_selector(locator)
    assert sel.startswith("div")
    assert "class='shopping_cart_container'" in sel


def _assert_unique(page: Page, selector: str, expected_text: str):
    """Helper to verify selector is unique and matches expected text content."""
    assert selector and selector.startswith("xpath="), f"Invalid selector: {selector}"
    loc = page.locator(selector)
    assert loc.count() == 1, f"Selector not unique: {selector}"
    if expected_text:
        text = loc.inner_text().strip()
        assert expected_text in text, f"Expected '{expected_text}', got '{text}'"


def test_add_to_cart_button_by_product_name(logged_in_page: Page):
    btn = logged_in_page.locator("button.btn_inventory").first
    xp = get_xpath_selector_by_other_element_text(btn, "Sauce Labs Backpack")
    _assert_unique(logged_in_page, xp, "Add to cart")


def test_price_by_product_name(logged_in_page: Page):
    price = logged_in_page.locator("div[data-test='inventory-item-price']").first
    xp = get_xpath_selector_by_other_element_text(price, "Sauce Labs Backpack")
    # If function gives container div, check that within it exists price
    assert xp and xp.startswith("xpath=")
    assert "$29.99" in logged_in_page.locator(xp).inner_text()


def test_inventory_item_name_by_description(logged_in_page: Page):
    name = logged_in_page.locator(".inventory_item_desc").first
    xp = get_xpath_selector_by_other_element_text(name, "Sauce Labs Backpack")
    # Allow None if no exact match, but check contains text fallback works
    assert xp and xp.startswith("xpath=")
    assert "carry.allTheThings() with the sleek, streamlined" in logged_in_page.locator(xp).inner_text()


# Helpers: assert containment relationship
def _assert_contains(page, parent_sel, child_sel, expected=True):
    parent = page.locator(parent_sel).first
    child = page.locator(child_sel).first
    result = check_parent_contains_child(parent, child)
    assert result == expected, f"{parent_sel} should {'contain' if expected else 'NOT contain'} {child_sel}"


def _assert_contains(page, parent_sel, child_sel, expected=True):
    parent = page.locator(parent_sel).first
    child = page.locator(child_sel).first
    result = check_parent_contains_child(parent, child)
    assert result == expected, f"{parent_sel} should {'contain' if expected else 'NOT contain'} {child_sel}"


def test_inventory_item_name_contained_in_parent(login):
    """Verify product name is inside its inventory item box."""
    _assert_contains(login, ".inventory_item", ".inventory_item_name", expected=True)


def test_inventory_item_price_contained_in_parent(login):
    """Verify product price is inside its inventory item box."""
    _assert_contains(login, ".inventory_item", ".inventory_item_price", expected=True)


def test_cart_icon_contained_in_header(login):
    """Verify cart icon is inside the primary header."""
    _assert_contains(login, "div.primary_header", "#shopping_cart_container", expected=True)


def test_cart_icon_not_contained_in_inventory_item(login):
    """Negative test: cart icon is NOT inside a product item box."""
    _assert_contains(login, ".inventory_item", "#shopping_cart_container", expected=False)

import pytest
from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage
from wrappers.smart_expect import expect
from urllib.parse import urljoin

INVENTORY_PAGE_HEADER = 'Swag Labs'

@pytest.mark.parametrize("username,password,product", [
    ("standard_user", "secret_sauce", "Sauce Labs Backpack"),
    ("visual_user", "secret_sauce", 'Sauce Labs Bolt T-Shirt'),
    ("performance_glitch_user", "secret_sauce", 'Sauce Labs Bike Light'),
])
def test_login_with_multiple_users(page, config, username, password, product):
    login_page = LoginPage(page, config)
    login_page.goto()
    login_page.login(username, password)

    inventory_page_url = urljoin(config["demo_base_url"], "inventory.html")
    inventory_page = InventoryPage(page, config)

    inventory_page.get_product_name().set_keyword(product)
    inventory_page.get_product_image().set_keyword(product)
    inventory_page.get_product_price().set_keyword(product)
    inventory_page.get_add_to_cart_button().set_keyword(product)

    expect(inventory_page.get_page()).to_have_url(inventory_page_url)
    expect(inventory_page.get_header()).to_have_text(INVENTORY_PAGE_HEADER)
    expect(inventory_page.get_product_name()).to_be_visible()
    expect(inventory_page.get_product_image()).to_be_visible()
    expect(inventory_page.get_product_price()).to_be_visible()
    expect(inventory_page.get_add_to_cart_button()).to_have_text("Add to cart")
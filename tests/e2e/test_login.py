import pytest
from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage


@pytest.mark.parametrize("username,password,product", [
    ('standard_user', 'secret_sauce', 'Sauce Labs Backpack'),
    ('visual_user', 'secret_sauce', 'Sauce Labs Bolt T-Shirt'),
    ('performance_glitch_user', 'secret_sauce', 'Sauce Labs Bike Light'),
])
def test_login_with_multiple_users(page, config, username, password, product):
    login_page = LoginPage(page, config)
    login_page.goto()
    login_page.login(username, password)

    inventory_page = InventoryPage(page, config)
    inventory_page.set_keyword(product)
    inventory_page.verify_page(product, "Add to cart")
import pytest
from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage

@pytest.mark.parametrize("username,password", [
    ("standard_user", "secret_sauce"),
    ("problem_user", "secret_sauce"),
    ("performance_glitch_user", "secret_sauce"),
])
def test_login_with_multiple_users(page, config, username, password):
    login_page = LoginPage(page, config)
    login_page.goto()
    login_page.login(username, password)

    inventory_page = InventoryPage(page, config)
    inventory_page.assert_on_inventory_page()

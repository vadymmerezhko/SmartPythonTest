import pytest
from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage


# Parametrize valid usernames and passwords
@pytest.mark.parametrize("username,password", [
    ("standard_user", "secret_sauce"),
    ("visual_user", "secret_sauce"),
    ("performance_glitch_user", "secret_sauce")
])

def test_login_with_valid_credentials(page, username, password):
    login_page = LoginPage(page)
    login_page.goto()
    login_page.login(username, password)

    inventory_page = InventoryPage(page)
    inventory_page.assert_on_inventory_page()

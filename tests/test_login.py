from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage

def test_login_with_valid_credentials(page):
    login_page = LoginPage(page)
    login_page.goto()
    login_page.login("standard_user", "secret_sauce")

    inventory_page = InventoryPage(page)
    inventory_page.assert_on_inventory_page()

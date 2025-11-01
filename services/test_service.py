from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage

class TestService:

    def login(self, page, config, username, password):
        login_page = LoginPage(page, config)
        login_page.goto()
        login_page.login(username, password)

    def verify_inventory_page(self, page, config, product, button_name):
        inventory_page = InventoryPage(page, config)
        inventory_page.set_keyword(product)
        inventory_page.verify_page(product, button_name)
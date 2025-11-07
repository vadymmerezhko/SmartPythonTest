from pages.inventory_page import InventoryPage
from pages.login_page import LoginPage

class TestService:

    def login(self, page, config, username, password):
        login_page = LoginPage(page, config)
        login_page.goto(config["demo_base_url"])
        login_page.fill_form(username, password)
        login_page.submit_form()

    def verify_inventory_page(self, page, config, product, button_name):
        inventory_page = InventoryPage(page, config)
        inventory_page.set_keyword(product)
        inventory_page.verify_page(product, button_name)
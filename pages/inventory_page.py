from playwright.sync_api import Page
from wrappers.smart_locator import SmartLocator
from wrappers.smart_expect import expect
from urllib.parse import urljoin

class InventoryPage(Page):
    HEADER = "Swag Labs"

    def __init__(self, page: Page, config: dict):
        self.page = page
        self.config = config
        self.URL = urljoin(config["demo_base_url"], "inventory.html")
        # Selectors
        self.header = SmartLocator(self, ".header_label")

    def assert_on_inventory_page(self):
        expect(self.page).to_have_url(self.URL)
        expect(self.header).to_have_text(self.HEADER)
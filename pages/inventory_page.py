from playwright.sync_api import Page
from wrappers.smart_locator import SmartLocator


class InventoryPage(Page):

    def __init__(self, page: Page, config: dict):
        self.page = page
        self.config = config
        # Selectors
        self.header = SmartLocator(self, ".header_label")

    def get_page(self):
        return self.page

    def get_header(self):
        return self.header

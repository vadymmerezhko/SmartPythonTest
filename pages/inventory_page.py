from playwright.sync_api import Page, expect

class InventoryPage(Page):
    URL = "https://www.saucedemo.com/inventory.html"
    HEADER = "Swag Labs"

    def __init__(self, page: Page):
        self.page = page
        # Selectors
        self.header = page.locator(".header_label")

    def assert_on_inventory_page(self):
        expect(self.page).to_have_url(self.URL)
        expect(self.header).to_have_text(self.HEADER);
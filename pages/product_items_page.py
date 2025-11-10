from playwright.sync_api import Page
from wrappers.smart_locator import SmartLocator
from wrappers.smart_page import SmartPage


class ProductItemsPage(SmartPage):

    def __init__(self, page: Page, config: dict):
        super().__init__(page, config)

        # Locators
        self.header = SmartLocator(self, "div[class='app_logo']")
        self.product_image = SmartLocator(self, "xpath=//div[@class='inventory_item'][.//*[normalize-space(text())='#KEYWORD']]//img[@class='inventory_item_img']")
        self.product_price = SmartLocator(self, "xpath=//div[@class='inventory_item_description'][.//*[normalize-space(text())='#KEYWORD']]//div[@class='inventory_item_price']")

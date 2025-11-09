from playwright.sync_api import Page
from wrappers.smart_locator import SmartLocator
from wrappers.smart_page import SmartPage


class CartPage(SmartPage):

    def __init__(self, page: Page, config: dict):
        super().__init__(page, config)

        # Locators
        self.header = SmartLocator(self, "span[data-test='title']")
        self.product_link = SmartLocator(self, "//*[normalize-space(text())='#KEYWORD']")
        self.product_price = SmartLocator(self, "xpath=//div[@class='cart_item_label'][.//*[normalize-space(text())='#KEYWORD']]//div[@class='inventory_item_price']")
        self.checkout_button = SmartLocator(self, "#checkout")
        self.remove_button = SmartLocator(self, "xpath=//div[@class='cart_item_label'][.//*[normalize-space(text())='#KEYWORD']]//button[@class='btn btn_secondary btn_small cart_button']")

    def remove_product(self):
        self.remove_button.click()
from playwright.sync_api import Page
from wrappers.smart_locator import SmartLocator


class InventoryPage(Page):

    def __init__(self, page: Page, config: dict):
        self.page = page
        self.config = config
        # Selectors
        self.header = SmartLocator(self, "div[class='app_logo']")
        self.product_name = SmartLocator(self, "//*[normalize-space(text())='#KEYWORD']")
        self.product_price = SmartLocator(self, "xpath=//div[@class='inventory_item_description'][.//*[normalize-space(text())='#KEYWORD']]//div[@class='inventory_item_price']")
        self.product_image = SmartLocator(self, "xpath=//div[@class='inventory_item'][.//*[normalize-space(text())='#KEYWORD']]//img[@class='inventory_item_img']")
        self.add_to_cart_button = SmartLocator(self, "xpath=//div[@class='inventory_item_description'][.//*[normalize-space(text())='#KEYWORD']]//button[@class='btn btn_primary btn_small btn_inventory ']")

    def get_page(self):
        return self.page

    def get_header(self) -> SmartLocator:
        return self.header

    def get_product_name(self):
        return self.product_name

    def get_product_price(self) -> SmartLocator:
        return self.product_price

    def get_product_image(self) -> SmartLocator:
        return self.product_image

    def get_add_to_cart_button(self) -> SmartLocator:
        return self.add_to_cart_button

    def set_keyword(self, keyword: str):
        self.product_name.set_keyword(keyword)
        self.product_image.set_keyword(keyword)
        self.product_price.set_keyword(keyword)
        self.add_to_cart_button.set_keyword(keyword)

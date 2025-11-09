from playwright.sync_api import Page
import re
from wrappers.smart_locator import SmartLocator
from wrappers.smart_expect import expect
from urllib.parse import urljoin

from wrappers.smart_page import SmartPage

INVENTORY_PAGE_HEADER = 'Swag Labs'

class InventoryPage(SmartPage):

    def __init__(self, page: Page, config: dict):
        super().__init__(page, config)
        # Selectors
        self.header = SmartLocator(self, "div[class='app_logo']")
        self.product_name = SmartLocator(self, "//*[normalize-space(text())='#KEYWORD']")
        self.product_price = SmartLocator(self, "xpath=//div[@class='inventory_item_description'][.//*[normalize-space(text())='#KEYWORD']]//div[@class='inventory_item_price']")
        self.product_image = SmartLocator(self, "xpath=//div[@class='inventory_item'][.//*[normalize-space(text())='#KEYWORD']]//img[@class='inventory_item_img']")
        self.add_to_cart_button = SmartLocator(self, "xpath=//div[@class='inventory_item_description'][.//*[normalize-space(text())='#KEYWORD']]//button[@class='btn btn_primary btn_small btn_inventory ']")
        self.cart_button = SmartLocator(self, "xpath=//div[.//*[normalize-space(text())='#KEYWORD']]//a[@class='shopping_cart_link']")
        self.inventory_page_url = urljoin(config['demo_base_url'], 'inventory.html')

    def verify_page(self, button_text):
        expect(self.page).to_have_url(self.inventory_page_url)
        expect(self.header).to_have_text(INVENTORY_PAGE_HEADER)
        expect(self.product_name).to_be_visible()
        expect(self.product_name).to_be_visible()
        expect(self.product_image).to_be_visible()
        expect(self.product_price).to_have_text(re.compile(r"^\$\s*\d", re.MULTILINE))
        expect(self.add_to_cart_button).to_have_text(button_text)

    def add_product_to_cart(self):
        self.add_to_cart_button.click()

    def open_cart_page(self):
        self.cart_button.click()

from playwright.sync_api import Page
from wrappers.smart_locator import SmartLocator
from wrappers.smart_page import SmartPage

class WebFormResultPage(SmartPage):

    def __init__(self, page: Page, config: dict):
        super().__init__(page, config)

        # Locators
        self.header = SmartLocator(self, "h1[class='display-6']")
        self.status = SmartLocator(self, "#message")

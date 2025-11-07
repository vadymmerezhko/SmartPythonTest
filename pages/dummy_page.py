from playwright.sync_api import Page
from wrappers.smart_locator import SmartLocator
from wrappers.smart_page import SmartPage


class DummyPage(SmartPage):

    def __init__(self, page: Page, config: dict):
        super().__init__(page, config)

        # SmartLocator fields (should get auto-getters)
        self.title = SmartLocator(self, "#title")
        self.username_input = SmartLocator(self, "#username")
        self.password_input = SmartLocator(self, "#password")

        # Non-locator and private fields (should be ignored)
        self._internal_state = "private_value"
        self.non_locator = "string_value"

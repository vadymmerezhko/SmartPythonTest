from playwright.sync_api import Page
from wrappers.smart_locator import SmartLocator
from wrappers.smart_page import SmartPage


class LoginPage(SmartPage):

    def __init__(self, page: Page, config: dict):
        super().__init__(page, config)

        # Locators
        self.username_input = SmartLocator(self, "#user-name")
        self.password_input = SmartLocator(self, "#password")
        self.login_button = SmartLocator(self, "#login-button")

    def fill_form(self, username, password):
        self.username_input.fill(username)
        self.password_input.fill(password)

    def submit_form(self):
        self.login_button.click()

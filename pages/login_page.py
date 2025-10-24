from playwright.sync_api import Page, expect
from wrappers.smart_locator import SmartLocator


class LoginPage:

    def __init__(self, page: Page, config: dict):
        self.page = page
        self.config = config
        self.URL = config["demo_base_url"]
        # Selectors
        self.username_input = SmartLocator(self, "#user-name")
        self.password_input = SmartLocator(self, "#password")
        self.login_button = SmartLocator(self, "#login-button")

    def goto(self):
        self.page.goto(self.URL)

    def login(self, username: str, password: str):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def assert_error_message(self, expected_text: str):
        expect(self.error_message).to_be_visible()
        expect(self.error_message).to_contain_text(expected_text)

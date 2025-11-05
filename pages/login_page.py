from playwright.sync_api import Page
from wrappers.smart_locator import SmartLocator


class LoginPage:

    def __init__(self, page: Page, config: dict):
        self.page = page
        self.config = config
        self.url = config["demo_base_url"]
        # Selectors
        self.username_input = SmartLocator(self, "#user-name")
        self.password_input = SmartLocator(self, "#password")
        self.login_button = SmartLocator(self, "#login-button")

    def add_placeholder(self, name, value):
        self.password_input.add_placeholder(name, value)

    def goto(self):
        self.page.goto(self.url)

    def login(self, username, password):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

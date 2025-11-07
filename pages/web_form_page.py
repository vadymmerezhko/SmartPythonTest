from decorators.class_decorators import auto_getters
from playwright.sync_api import Page
from wrappers.smart_locator import SmartLocator
from wrappers.smart_page import SmartPage

@auto_getters
class WebFormPage(SmartPage):

    def __init__(self, page: Page, config: dict):
        super().__init__(page, config)

        # Locators
        self.header = SmartLocator(self, "h1[class='display-6']")
        self.text_input = SmartLocator(self, "#my-text-id")
        self.password_input = SmartLocator(self, "input[name='my-password']")
        self.textarea_input = SmartLocator(self, "textarea[name='my-textarea']")
        self.disabled_input = SmartLocator(self, "input[name='my-disabled']")
        self.readonly_input = SmartLocator(self, "input[name='my-readonly']")
        self.dropdown_select = SmartLocator(self, "select[name='my-select']")
        self.dropdown_data_list = SmartLocator(self, "input[name='my-datalist']")
        self.file_input = SmartLocator(self, "input[name='my-file']")
        self.checkbox1 = SmartLocator(self, "#my-check-1")
        self.checkbox2 = SmartLocator(self, "#my-check-2")
        self.radiobutton1 = SmartLocator(self, "#my-radio-1")
        self.radiobutton2 = SmartLocator(self, "#my-radio-2")
        self.color_picker = SmartLocator(self, "input[name='my-colors']")
        self.date_picker = SmartLocator(self, "input[name='my-date']")
        self.example_range = SmartLocator(self, "input[name='my-range']")
        self.submit_button = SmartLocator(self, "button[class='btn btn-outline-primary mt-3']")

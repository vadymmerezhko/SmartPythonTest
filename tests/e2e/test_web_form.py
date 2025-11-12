import pytest
import re
from pages.web_form_page import WebFormPage
from pages.web_form_result_page import WebFormResultPage
from wrappers.smart_expect import expect

WEB_FORM_URL = "https://www.selenium.dev/selenium/web/web-form.html"

# This test is just for testing SmartPage, SmartLocator and SmartExcept
def test_web_form_page(page, config):
    web_form_page = WebFormPage(page, config)
    # Verify web form default values
    web_form_page.goto(WEB_FORM_URL)
    expect(web_form_page.header).to_have_text('Web form!')
    expect(web_form_page.disabled_input).to_have_value('')
    expect(web_form_page.readonly_input).to_have_value('Readonly input')
    expect(web_form_page.checkbox1).to_be_checked()
    expect(web_form_page.radiobutton1).to_be_checked()
    expect(web_form_page.color_picker).to_have_value('#563d7c')
    expect(web_form_page.example_range).to_have_value('5')

    # Fill the form
    web_form_page.text_input.fill('Text input')
    web_form_page.password_input.fill('Secret')
    web_form_page.textarea_input.fill('Some text in textarea')
    web_form_page.textarea_input.fill('Some text in textarea')
    web_form_page.dropdown_select.select_option('2')
    web_form_page.dropdown_data_list.fill('Los Angeles')
    web_form_page.file_input.set_input_files('README.md')
    web_form_page.checkbox1.uncheck()
    web_form_page.checkbox2.check()
    web_form_page.radiobutton2.check()
    web_form_page.color_picker.fill('#b21f75')
    web_form_page.date_picker.fill('11/07/2025')
    web_form_page.example_range.fill('3')

    # Verify new values on the form
    expect(web_form_page.text_input).to_have_value('Text input')
    expect(web_form_page.textarea_input).to_have_value('Some text in textarea')
    expect(web_form_page.dropdown_select).to_have_value('2')
    expect(web_form_page.dropdown_data_list).to_have_value('Los Angeles')
    expect(web_form_page.file_input).to_have_value(re.compile(r".*README\.md$"))
    expect(web_form_page.checkbox1).not_to_be_checked()
    expect(web_form_page.checkbox2).to_be_checked()
    expect(web_form_page.radiobutton1).not_to_be_checked()
    expect(web_form_page.radiobutton2).to_be_checked()
    expect(web_form_page.color_picker).to_have_value('#b21f75')
    expect(web_form_page.date_picker).to_have_value('11/07/2025')
    expect(web_form_page.example_range).to_have_value('3')

    # submit the form
    web_form_page.submit_button.click()

    # Verify web form result page
    web_form_result_page = WebFormResultPage(page, config)
    expect(web_form_result_page.header).to_have_text('Form submitted')
    expect(web_form_result_page.status).to_have_text('Received!')
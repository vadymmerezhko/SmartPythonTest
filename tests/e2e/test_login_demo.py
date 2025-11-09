import pytest
from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage
from wrappers.smart_expect import expect

def test_simple_login(page, config):
    login_page = LoginPage(page, config)
    login_page.add_placeholder('demo_base_url')
    login_page.goto('#DEMO_BASE_URL#')
    login_page.fill_form('standard_user', 'secret_sauce')
    login_page.submit_form()

    product = 'Sauce Labs Bike Light'
    inventory_page = InventoryPage(page, config)
    expect(inventory_page.header).to_have_text('Swag Labs')
    inventory_page.set_keyword(product)
    expect(inventory_page.product_price).to_have_text('$9.99')
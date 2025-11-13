import pytest
from pages.login_page import LoginPage
from pages.product_items_page import ProductItemsPage
from wrappers.smart_expect import expect

@pytest.mark.parametrize("product,price", [
    ('Sauce Labs Bike Light', '$9.99'),
    ('Sauce Labs Backpack', '$29.99')
])
def test_product_items(page, config, product, price):
    username = 'standard_user'
    password = 'secret_sauce'
    login_page = LoginPage(page, config)
    login_page.add_placeholder('demo_base_url')
    login_page.goto('#DEMO_BASE_URL#')
    login_page.fill_form(username, password)
    login_page.submit_form()

    product_items_page = ProductItemsPage(page, config)
    expect(product_items_page.header).to_have_text('Swag Labs')
    product_items_page.set_keyword(product)
    expect(product_items_page.product_image).to_be_visible()
    expect(product_items_page.product_price).to_have_text(price)
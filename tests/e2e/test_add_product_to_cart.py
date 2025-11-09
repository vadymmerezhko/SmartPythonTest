import pytest
from pages.cart_page import CartPage
from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage
from wrappers.smart_expect import expect


def test_add_product_to_cart(page, config):
    login_page = LoginPage(page, config)
    login_page.add_placeholder('demo_base_url')
    login_page.goto('#DEMO_BASE_URL#')
    login_page.fill_form('standard_user', 'secret_sauce')
    login_page.submit_form()

    product_name = 'Sauce Labs Bike Light'
    product_price = '$9.99'
    inventory_page = InventoryPage(page, config)
    inventory_page.set_keyword(product_name)
    expect(inventory_page.product_price).to_have_text(product_price)
    inventory_page.add_product_to_cart()
    expect(inventory_page.cart_button).to_have_text('1')
    # Reset keyword because open cart button does not relate to product name
    inventory_page.reset_keyword()
    inventory_page.open_cart_page()

    cart_page = CartPage(page, config)
    expect(cart_page.header).to_have_text('Your Cart')
    expect(cart_page.checkout_button).to_have_text('Checkout')
    cart_page.set_keyword(product_name)
    expect(cart_page.product_link).to_have_text(product_name)
    expect(cart_page.product_price).to_have_text(product_price)
    expect(cart_page.remove_button).to_have_text('Remove')
    cart_page.remove_product()
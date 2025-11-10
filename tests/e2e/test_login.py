import pytest
from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage
from services.test_service import TestService

@pytest.mark.parametrize("username,password,product", [
    ('standard_user', 'secret_sauce', 'Sauce Labs Backpack'),
    ('visual_user', 'secret_sauce', 'Sauce Labs Bolt T-Shirt'),
    ('performance_glitch_user', 'secret_sauce', 'Sauce Labs Bike Light')
])
# Page objects are used directly in the test
def test_login_with_multiple_users(page, config, username, password, product):
    login_page = LoginPage(page, config)
    login_page.goto(config["demo_base_url"])
    login_page.fill_form(username, password)
    login_page.submit_form()

    inventory_page = InventoryPage(page, config)
    inventory_page.set_keyword(product)
    inventory_page.verify_page('Add to cart')

# Test with test service
@pytest.mark.parametrize("username,password,product", [
    ('standard_user', 'secret_sauce', 'Sauce Labs Backpack'),
    ('visual_user', 'secret_sauce', 'Sauce Labs Bolt T-Shirt')
])
def test_login_with_multiple_users_and_test_service(page, config, username, password, product):

    test_service = TestService()
    test_service.login(page, config, username, password)
    test_service.verify_inventory_page(page, config, product, 'Add to cart')

# Test with key -> value placeholder
@pytest.mark.parametrize("username,password,product", [
    ('standard_user', '#PASSWORD#', 'Sauce Labs Backpack'),
    ('visual_user', '#PASSWORD#', 'Sauce Labs Bolt T-Shirt')
])
def test_login_with_key_value_placeholder(page, config, username, password, product):
    login_page = LoginPage(page, config)
    login_page.add_placeholder('password', 'secret_sauce')
    login_page.add_placeholder("demo_base_url")
    login_page.goto(config["demo_base_url"])
    login_page.fill_form(username, password)
    login_page.submit_form()

    inventory_page = InventoryPage(page, config)
    inventory_page.set_keyword(product)
    inventory_page.verify_page('Add to cart')

# Test with key-only placeholder
def test_login_with_key_only_placeholder(page, config):
    login_page = LoginPage(page, config)
    login_page.add_placeholder('demo_base_url')
    login_page.goto('#DEMO_BASE_URL#')
    login_page.fill_form('standard_user', 'secret_sauce')
    login_page.submit_form()

    product = 'Sauce Labs Backpack'
    inventory_page = InventoryPage(page, config)
    inventory_page.set_keyword(product)
    inventory_page.add_placeholder('Test_placeholder')
    inventory_page.verify_page('#TEST_PLACEHOLDER#')
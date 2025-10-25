import pytest
from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage
from wrappers.smart_expect import expect
from urllib.parse import urljoin

INVENTORY_PAGE_HEADER = 'Swag Labs'

@pytest.mark.parametrize("username,password", [
    ("standard_user", "secret_sauce"),
    ("problem_user", "secret_sauce"),
    ("performance_glitch_user", "secret_sauce"),
])
def test_login_with_multiple_users(page, config, username, password):
    login_page = LoginPage(page, config)
    login_page.goto()
    login_page.login(username, password)

    inventory_page_url = urljoin(config["demo_base_url"], "inventory.html")
    inventory_page = InventoryPage(page, config)
    page = inventory_page.get_page()
    header = inventory_page.get_header()
    expect(page).to_have_url(inventory_page_url)
    expect(header).to_have_text(INVENTORY_PAGE_HEADER)
import pytest
import tempfile
import textwrap
import os
from utils.code_utils import (get_caller_info,
                              get_function_parameters_index_map,
                              update_value_in_function_call,
                              replace_variable_assignment,
                              get_parameter_index_from_function_def,
                              get_data_provider_names_map,
                              replace_variable_in_data_provider)


def helper_function():
    # This will be line number X, we assert against this
    return get_caller_info(1)

def test_get_caller_info():
    filename, lineno, code = helper_function()

    # Ensure the filename is this test file
    assert os.path.basename(filename) == os.path.basename(__file__)

    # Ensure the code context contains the call line
    assert "return get_caller_info(1)" in code

    # Ensure the line number matches the helper_function call
    # get the source lines to validate the exact line number
    import linecache
    line_text = linecache.getline(filename, lineno).strip()
    assert line_text == "return get_caller_info(1)"

def test_get_param_index_map_with_variables_with_indent():
    expr = "    login_page.login(username, password)"
    result = get_function_parameters_index_map(expr)
    assert result == {0: "username", 1: "password"}

def test_get_param_index_map_with_literal_and_var():
    expr = "page.fill(username, 'secret', retries)"
    result = get_function_parameters_index_map(expr)
    assert result == {0: "username", 1: "'secret'", 2: "retries"}

def test_get_param_index_map_with_numbers():
    expr = "math.pow(2, exponent)"
    result = get_function_parameters_index_map(expr)
    assert result == {0: "2", 1: "exponent"}

def test_get_param_index_map_with_none_value():
    expr = "math.pow(2, None)"
    result = get_function_parameters_index_map(expr)
    assert result == {0: "2", 1: "None"}

def test_update_none_argument_to_string():
    line = "login_page.login(None, password)"
    result = update_value_in_function_call(line, 0, "None","'admin'")
    assert result == "login_page.login('admin', password)"

def test_update_none_argument_to_string_with_indent():
    line = "    login_page.login(None, None)    "
    result = update_value_in_function_call(line, 0, "None", "username")
    result = update_value_in_function_call(result, 1, "None", "password")
    assert result == "    login_page.login(username, password)    "

def test_update_with_wrong_old_value():
    line = "login_page.login(username, password)"
    result = update_value_in_function_call(line, 0, "None","'admin'")
    assert result == None

TEST_FILE_CONTENT = """import pytest
from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage
from wrappers.smart_expect import expect
from urllib.parse import urljoin

INVENTORY_PAGE_HEADER = 'Swag Labs'

@pytest.mark.parametrize("username,password,product", [
    ("standard_user", "secret_sauce", "Sauce Labs Backpack"),
    ("visual_user", "secret_sauce", 'Sauce Labs Bolt T-Shirt'),
    ("performance_glitch_user", "secret_sauce", 'Sauce Labs Bike Light'),
])
def test_login_with_multiple_users(page, config, username, password, product):
    login_page = LoginPage(page, config)
    login_page.goto()
    login_page.login(None, None)

    inventory_page_url = urljoin(config["demo_base_url"], "inventory.html")
    inventory_page = InventoryPage(page, config)
    inventory_page.set_keyword(product)
"""

def test_update_none_values_in_function_call():
    # Create a temporary test file
    with tempfile.NamedTemporaryFile("w+", suffix="_test.py", delete=False) as tmp:
        tmp.write(TEST_FILE_CONTENT)
        tmp_path = tmp.name

    try:
        updated_lines = []
        with open(tmp_path, "r", encoding="utf-8") as f:
            for line in f:
                if "login_page.login(None, None)" in line:
                    # First replace first None -> username
                    line = update_value_in_function_call(line, 0, "None", "username") or line
                    # Then replace second None -> password
                    line = update_value_in_function_call(line, 1, "None", "password") or line
                updated_lines.append(line)

        # Join updated file
        updated_content = "".join(updated_lines)

        # Check that None was replaced correctly
        assert "login_page.login(username, password)" in updated_content

    finally:
        os.remove(tmp_path)

def test_update_none_argument_to_string():
    line = "login_page.login(None, password)"
    result = update_value_in_function_call(line, 0, "None", "username")
    assert result == "login_page.login(username, password)"


def test_update_none_argument_to_string_with_indent():
    line = "    login_page.login(None, None)    "
    result = update_value_in_function_call(line, 0, "None", "username")
    result = update_value_in_function_call(result, 1, "None", "password")
    assert result == "    login_page.login(username, password)    "


def test_replace_with_single_quotes():
    line = "username = 'admin'"
    result = replace_variable_assignment(line, "username", "'root'")
    assert result == "username = 'root'"


def test_replace_with_double_quotes_with_indent():
    line = '    username = "admin"'
    result = replace_variable_assignment(line, "username", "'guest'")
    assert result == "    username = 'guest'"  # preserves 4 spaces


def test_replace_without_indent():
    line = 'username = "admin"'
    result = replace_variable_assignment(line, "username", "'guest'")
    assert result == "username = 'guest'"


def test_replace_with_none():
    line = "username=None"
    result = replace_variable_assignment(line, "username", "'new_user'")
    assert result == "username = 'new_user'"


def test_replace_case_insensitive():
    line = 'USERNAME=  "admin"'
    result = replace_variable_assignment(line, "username", "None")
    assert result == "USERNAME = None"


def test_no_match_returns_none():
    line = "password = 'secret'"
    result = replace_variable_assignment(line, "username", "'root'")
    assert result is None


def create_temp_file(code: str) -> str:
    """Helper to create a temporary python file with given code."""
    tmp = tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False)
    tmp.write(textwrap.dedent(code))
    tmp.flush()
    tmp.close()
    return tmp.name


def test_plain_parameters():
    code = """
    class LoginPage:
        def login(self, username, password):
            self.username_input.fill(username)
            self.password_input.fill(password)
    """
    path = create_temp_file(code)

    try:
        # find line numbers
        with open(path, "r") as f:
            lines = f.readlines()

        line_username = next(i+1 for i, l in enumerate(lines) if "fill(username)" in l)
        line_password = next(i+1 for i, l in enumerate(lines) if "fill(password)" in l)

        assert get_parameter_index_from_function_def(path, line_username, 0) == 0
        assert get_parameter_index_from_function_def(path, line_password, 0) == 1
    finally:
        os.remove(path)


def test_parameters_with_type_annotations_and_return_type():
    code = """
    class LoginPage:
        def login(self, username: str, password: str) -> bool:
            self.username_input.fill(username)
            self.password_input.fill(password)
    """
    path = create_temp_file(code)

    try:
        with open(path, "r") as f:
            lines = f.readlines()
        line_username = next(i+1 for i, l in enumerate(lines) if "fill(username)" in l)
        line_password = next(i+1 for i, l in enumerate(lines) if "fill(password)" in l)

        assert get_parameter_index_from_function_def(path, line_username, 0) == 0
        assert get_parameter_index_from_function_def(path, line_password, 0) == 1
    finally:
        os.remove(path)


def test_parameters_with_defaults():
    code = '''
    class LoginPage:
        def login(self, username: str, password="secret"):
            self.username_input.fill(username)
            self.password_input.fill(password)
    '''
    path = create_temp_file(code)

    try:
        with open(path, "r") as f:
            lines = f.readlines()
        line_username = next(i+1 for i, l in enumerate(lines) if "fill(username)" in l)
        line_password = next(i+1 for i, l in enumerate(lines) if "fill(password)" in l)

        assert get_parameter_index_from_function_def(path, line_username, 0) == 0
        assert get_parameter_index_from_function_def(path, line_password, 0) == 1
    finally:
        os.remove(path)


def test_returns_minus_one_if_not_found():
    code = """
    def unrelated():
        print("no calls here")
    """
    path = create_temp_file(code)

    try:
        with open(path, "r") as f:
            lines = f.readlines()
        line_no_call = next(i+1 for i, l in enumerate(lines) if "print" in l)

        assert get_parameter_index_from_function_def(path, line_no_call, 0) == -1
    finally:
        os.remove(path)


def test_basic_case():
    line = '@pytest.mark.parametrize("username,password,product", ['
    result = get_data_provider_names_map(line)
    assert result == {"username": 0, "password": 1, "product": 2}

def test_single_parameter():
    line = "@pytest.mark.parametrize('user', ["
    result = get_data_provider_names_map(line)
    assert result == {"user": 0}

def test_spaces_and_tabs():
    line = '@pytest.mark.parametrize(" username ,  password , product ", ['
    result = get_data_provider_names_map(line)
    assert result == {"username": 0, "password": 1, "product": 2}

def test_double_and_single_quotes():
    line1 = "@pytest.mark.parametrize('username,password', ["
    line2 = '@pytest.mark.parametrize("username,password", ['
    assert get_data_provider_names_map(line1) == {"username": 0, "password": 1}
    assert get_data_provider_names_map(line2) == {"username": 0, "password": 1}

def test_no_parametrize_returns_empty_dict():
    line = "def some_function():"
    result = get_data_provider_names_map(line)
    assert result == {}

def test_replace_first_column():
    row = '("standard_user", "secret_sauce", "Sauce Labs Backpack"),'
    updated = replace_variable_in_data_provider(row, 0, '"admin"')
    assert updated == "('admin', 'secret_sauce', 'Sauce Labs Backpack'),"

def test_replace_middle_column():
    row = '("visual_user", "secret_sauce", "Sauce Labs Bolt T-Shirt"),'
    updated = replace_variable_in_data_provider(row, 1, '"new_secret"')
    assert updated == "('visual_user', 'new_secret', 'Sauce Labs Bolt T-Shirt'),"

def test_replace_last_column():
    row = '("performance_glitch_user","secret_sauce","Sauce Labs Bike Light"),'
    updated = replace_variable_in_data_provider(row, 2, '"Updated Product"')
    assert updated == "('performance_glitch_user', 'secret_sauce', 'Updated Product'),"

def test_invalid_index_returns_original():
    row = '("standard_user","secret_sauce","Sauce Labs Backpack"),'
    updated = replace_variable_in_data_provider(row, 5, '"ignored"')
    assert updated ==  None

def test_not_a_tuple_returns_original():
    row = '"justastring",'
    updated = replace_variable_in_data_provider(row, 0, '"newstring"')
    assert updated == None

def test_preserve_comma_at_end():
    row = '     ("user", "pass")'
    updated = replace_variable_in_data_provider(row, 0, '"changed"')
    assert updated == "     ('changed', 'pass')"

import pytest
import inspect
from utils.code_utils import normalize_args


# --- Fake functions to simulate Playwright Locator methods --- #

def fake_fill(value: str, *, timeout: int = None, no_wait_after: bool = None):
    return f"filled {value} with timeout={timeout}"


def fake_type(text: str, *, delay: int = 0):
    return f"typed {text} with delay={delay}"


def fake_press(key: str, *, timeout: int = None):
    return f"pressed {key} with timeout={timeout}"


# --- Fake functions to simulate Playwright Locator methods --- #

def fake_fill(value: str, *, timeout: int = None, no_wait_after: bool = None):
    return f"filled {value} with timeout={timeout}"


def fake_type(text: str, *, delay: int = 0):
    return f"typed {text} with delay={delay}"


def fake_press(key: str, *, timeout: int = None):
    return f"pressed {key} with timeout={timeout}"


# --- Tests --- #

def test_fill_with_positional():
    args, kwargs = normalize_args(fake_fill, "admin")
    assert args == ("admin",)
    assert kwargs == {}


def test_fill_with_keyword_value():
    args, kwargs = normalize_args(fake_fill, value="guest")
    assert args == ("guest",)
    assert kwargs == {}


def test_fill_with_timeout_keyword():
    args, kwargs = normalize_args(fake_fill, value="root", timeout=5000)
    assert args == ("root",)
    assert kwargs == {"timeout": 5000}


def test_type_with_keyword_text():
    args, kwargs = normalize_args(fake_type, text="hello")
    assert args == ("hello",)
    assert kwargs == {}


def test_type_with_delay_keyword():
    args, kwargs = normalize_args(fake_type, "hi", delay=100)
    assert args == ("hi",)
    assert kwargs == {"delay": 100}


def test_press_with_positional():
    args, kwargs = normalize_args(fake_press, "Enter")
    assert args == ("Enter",)
    assert kwargs == {}


def test_press_with_keyword():
    args, kwargs = normalize_args(fake_press, key="Tab")
    assert args == ("Tab",)
    assert kwargs == {}


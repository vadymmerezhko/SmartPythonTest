import os
from conftest import get_current_param_row
import pathlib
import re
import tkinter as tk
from common.constnts import KEYWORD_PLACEHOLDER
from playwright.sync_api import Page
from tkinter import messagebox, simpledialog
from utils.web_utils import (select_element_on_page,
                             get_element_value_or_text,
                             get_unique_element_selector)
from utils.code_utils import (get_caller_info,
                              get_function_parameters_index_map,
                              update_value_in_function_call,
                              get_parameter_index_from_function_def,
                              replace_variable_assignment,
                              get_data_provider_names_map,
                              replace_variable_in_data_provider)
from utils.text_utils import replace_line_in_text

def update_value_in_source_file(arg_type, file_path, lineno, param_index, new_value):
    param_name = None

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        new_content = content

    current_line = len(new_content.splitlines())

    with open(file_path, "r", encoding="utf-8") as f:
        for line in reversed(f.readlines()):

            if current_line == lineno:
                updated_line = update_value_in_function_call(
                    line, param_index, "None", f"'{new_value}'")

                if updated_line is not None:
                    new_content = replace_line_in_text(new_content, current_line, updated_line)
                    break
                else:
                    params_map = get_function_parameters_index_map(line)
                    param_name = params_map[param_index]

            elif current_line < lineno:
                updated_line = replace_variable_assignment(
                    line, param_name, f"'{new_value}'")

                if updated_line is not None:
                    new_content = replace_line_in_text(new_content, current_line, updated_line)

            current_line = current_line - 1

    if new_content == content:
        # Fix None value in the data provider
        current_line = 1
        data_row_index = -1
        column_index = -1
        in_data_block = False
        target_row_index = get_current_param_row()

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f.readlines():

                if line.strip().startswith("@pytest.mark.parametrize"):
                    data_names_map = get_data_provider_names_map(line)
                    column_index = data_names_map[param_name]

                    data_row_index = 0
                    in_data_block = True

                elif in_data_block:
                    if data_row_index == target_row_index:
                        updated_line = replace_variable_in_data_provider(
                            line, column_index, f"'{new_value}'")

                        if updated_line is not None:
                            new_content = replace_line_in_text(
                                new_content, current_line, updated_line)
                        else:
                            messagebox.askokcancel(
                                f"Missing {arg_type} valur",
                                f"None {arg_type} cannot be fixed\n"
                                f"Code line: {line}\n"
                                f"Row index {target_row_index}\n"
                                f"Column index: {column_index}\n"
                                "Or OK or Cancel to terminate record mode."
                            )
                            raise RuntimeError("Record mode interrupted by user.")

                    data_row_index = data_row_index + 1

                current_line = current_line + 1

    # Save to the test file:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

def fix_none_value_in_file(arg_type, page, file_path, lineno, code, param_index):

    while True:
        file_name = os.path.basename(file_path)

        new_value = simpledialog.askstring(
            f"Missing {arg_type} value",
            f"None {arg_type}\n"
            f"File {file_name}:{lineno}\n"
            f"Code line: {code}\n"
            f"Index: {param_index}\n"
            f"Enter correct {arg_type} value and click OK.\n"
            f"Or click OK, select {arg_type} value and press Ctrl.\n"
            "Or click Cancel to terminate record mode.",
            initialvalue="Some value"
        )

        if not new_value:
            raise RuntimeError("Record mode interrupted by user.")

        if new_value == "Some value":
            selected_locator = select_element_on_page(page)
            new_value = get_element_value_or_text(selected_locator)

            result = messagebox.askokcancel(
                "Value confirmation",
                f"Value for {arg_type}\n"
                f"File: {file_name}:{lineno}\n"
                f"Code line: {code}\n"
                f"Index: {param_index}\n"
                f"New value: {new_value}\n"
                "Click OK to confirm and save this value.\n"
                "Or click Cancel to retry."
            )
            if result:
                break
            else:
                continue
        else:
            break

    update_value_in_source_file(arg_type, file_path, lineno, param_index, new_value)
    return new_value

def fix_noname_parameter_none_value(arg_type, page, index):
    param_index = -1
    in_stack_blok = False

    for i in range(3, 10):
        # Fix literal constant values in the test file
        filename, lineno, code = get_caller_info(i)
        simple_file_name = os.path.basename(filename)

        # Get parameter id from function definition in the page object file.
        if ("/pages/" in filename or "\\pages\\" in filename) and simple_file_name.endswith("_page.py"):
            in_stack_blok = True
            param_index = get_parameter_index_from_function_def(filename, lineno, index)

        # Fix None value in the test file.
        elif ("/tests/" in filename or "\\tests\\" in filename) and simple_file_name.startswith("test_"):

            if param_index == -1:
                messagebox.askokcancel(
                    "Missing value",
                    f"None {arg_type} in cannot be fixed\n"
                    f"Line number: {lineno}\n"
                    f"Code line: {code}\n"
                    f"Index: {param_index}\n"
                    "Or OK or Cancel to terminate record mode."
                )
                raise RuntimeError("Record mode interrupted by user.")

            return fix_none_value_in_file(arg_type, page, filename, lineno, code, param_index)

        elif in_stack_blok:
            param_index = get_parameter_index_from_function_def(filename, lineno, param_index)


def handle_missing_locator(page: Page, cache_key: str, selector: str, keyword: str):
    root = tk.Tk()
    root.withdraw()

    while True:

        if selector.strip() == "":
           selector = "Element locator"

        new_selector = simpledialog.askstring(
            "Locator failed",
            f"Locator failed: '{selector}'\n"
            f"Element name: '{cache_key}'\n"
            f"Keyword: {keyword}\n"
            f"Enter new locator and click OK to save it.\n"
            "Or click OK, select element and press Ctrl button.\n"
            "Or click Cancel to terminate record mode.",
            initialvalue=selector
        )

        if not new_selector:
            raise RuntimeError("Record mode interrupted by user.")

        if new_selector == selector:
            selected_locator = select_element_on_page(page)
            new_selector = get_unique_element_selector(selected_locator, keyword)

            result = messagebox.askokcancel(
                "Locator confirmation",
                f"Locator found: '{new_selector}'\n"
                f"Element name: '{cache_key}'\n"
                f"Keyword: {keyword}\n"
                "Click OK to confirm and save locator.\n"
                "Or click Cancel to keep updating."
            )

            if result:
                break
            else:
                continue

    return new_selector


def update_source_file(source_file: str, field_name: str, cache_key: str, keyword: str, new_selector: str):
    # replace keyword with placeholder value if not None
    if keyword:
        new_selector = new_selector.replace(keyword, KEYWORD_PLACEHOLDER)

    path = pathlib.Path(source_file)
    text = path.read_text(encoding="utf-8")

    pattern = rf'self\.{field_name}\s*=\s*SmartLocator\(.*?\)'
    replacement = f'self.{field_name} = SmartLocator(self, "{new_selector}")'
    new_text = re.sub(pattern, replacement, text)

    if text != new_text:
        path.write_text(new_text, encoding="utf-8")
    else:
        print(f"[SmartLocator] Warning: could not patch {cache_key} in {path}")

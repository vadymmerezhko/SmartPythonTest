import os
import sys
from conftest import get_current_param_row
import pathlib
import re
import tkinter as tk
from enums.update_type import UpdateType
from common.constnts import KEYWORD_PLACEHOLDER
from playwright.sync_api import Page
from tkinter import messagebox, simpledialog
from helpers.placeholder_manager import PlaceholderManager
from utils.web_utils import (select_element_on_page,
                             get_element_value_or_text,
                             get_unique_element_selector,
                             replace_br_tags_with_paragraph_tags)
from utils.code_utils import (get_caller_info,
                              get_function_parameters_index_map,
                              update_value_in_function_call,
                              get_parameter_index_from_function_def,
                              replace_variable_assignment,
                              get_data_provider_names_map,
                              replace_variable_in_data_provider,
                              get_parameter_name_by_index)
from utils.text_utils import replace_line_in_text


def update_value_in_source_file(arg_type: str, file_path: str, lineno: int,
                                param_index: int, old_value: str, new_value: str) -> UpdateType:
    param_name = None
    data_provider_lineno = None
    update_type = None

    if old_value != "None":
        old_value = f"'{old_value}'"

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        new_content = content

    current_line = len(new_content.splitlines()) + 1

    with open(file_path, "r", encoding="utf-8") as f:
        for line in reversed(f.readlines()):
            current_line = current_line - 1

            if current_line > lineno:
                continue

            if current_line == lineno:

                updated_line = update_value_in_function_call(
                    line, param_index, old_value, f"'{new_value}'")

                if updated_line is not None:
                    new_content = replace_line_in_text(new_content, current_line, updated_line)
                    update_type = UpdateType.INLINE
                    break
                else:
                    params_map = get_function_parameters_index_map(line)
                    param_name = params_map[param_index]

            elif current_line < lineno:
                updated_line = replace_variable_assignment(
                    line, param_name, f"'{new_value}'")

                if updated_line is not None:
                    new_content = replace_line_in_text(new_content, current_line, updated_line)
                    update_type = UpdateType.ASSIGNMENT
                    break

            if line.strip().startswith("@pytest.mark.parametrize") and current_line < lineno:
                data_provider_lineno = current_line
                break

    if new_content == content:
        # Fix None value in the data provider
        current_line = 0
        data_row_index = -1
        column_index = -1
        in_data_block = False
        target_row_index = get_current_param_row()

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f.readlines():
                current_line = current_line + 1

                if current_line < data_provider_lineno:
                    continue

                if current_line == data_provider_lineno:
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
                            update_type = UpdateType.DATA_PROVIDER
                            break
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

    # Save to the test file:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return update_type

def fix_value_in_file(arg_type: str, page: Page, file_path: str, lineno: int,
                      code: str, param_index: int, old_value: str,
                      placeholder_manager: PlaceholderManager) -> tuple:

    while True:
        file_name = os.path.basename(file_path)
        param_name = get_parameter_name_by_index(code, param_index)

        new_value = simpledialog.askstring(
            f"Fix failed {arg_type} value",
            f"File : {file_name}:{lineno}\n"
            f"Code line: {code}\n"
            f"Parameter index: {param_index}\n"
            f"Parameter name: {param_name}\n"
            f"Current value: {old_value}\n"
            f"Enter correct {arg_type} value and click OK.\n"
            f"Or click OK, select {arg_type} value and press Ctrl.\n"
            "Or click Cancel to terminate record mode.",
            initialvalue=old_value
        )

        if new_value is None:
            system_exit()

        if new_value == old_value:
            replace_br_tags_with_paragraph_tags(page, "body")
            selected_locator = select_element_on_page(page)
            new_value = get_element_value_or_text(selected_locator)

            result = messagebox.askokcancel(
                f"Confirm {arg_type} value",
                f"File: {file_name}:{lineno}\n"
                f"Code line: {code}\n"
                f"Index: {param_index}\n"
                f"Old value: {old_value}\n"
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

    new_value = placeholder_manager.replace_values_with_placeholders(new_value)
    update_type = update_value_in_source_file(arg_type, file_path, lineno, param_index, old_value, new_value)

    return (update_type, new_value)

def fix_noname_parameter_value(arg_type: str, page: Page, index: int, old_value: str,
                               placeholder_manager: PlaceholderManager) -> tuple:
    param_index = index
    in_stack_block = False

    # Start from the 4th level where values is used by Playwright method
    for i in range(3, 10):
        # Fix literal constant values in the test file
        filename, lineno, code = get_caller_info(i)
        next_filename = get_caller_info(i + 1)[0]

        if "/pages/" in filename or "\\pages\\" in filename:
            # Get parameter id from function definition in the page object file.
            param_index = get_parameter_index_from_function_def(filename, lineno, param_index)
            in_stack_block = True
            continue

        # Fix None value in the test file.
        if  next_filename.endswith("python.py"):

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

            return fix_value_in_file(arg_type, page, filename,lineno, code, param_index,
                                     old_value, placeholder_manager)

        if in_stack_block:
            # Get parameter id from function definition in the page object file.
            param_index = get_parameter_index_from_function_def(filename, lineno, param_index)


def handle_missing_locator(page: Page, cache_key: str, selector: str, keyword: str) -> str:
    root = tk.Tk()
    root.withdraw()

    while True:

        new_selector = simpledialog.askstring(
            "Fix failed selector",
            f"Element name: '{cache_key}'\n"
            f"Keyword: {keyword}\n"
            f"Failed selector: '{selector}'\n"
            f"Enter new selector and click OK to save it.\n"
            "Or click OK, select element and press Ctrl button.\n"
            "Or click Cancel to terminate record mode.",
            initialvalue=selector
        )

        if new_selector is None:
            system_exit()

        if new_selector == selector:
            selected_locator = select_element_on_page(page)
            new_selector = get_unique_element_selector(selected_locator, keyword)

            result = messagebox.askokcancel(
                "Confirm selector",
                f"Element name: '{cache_key}'\n"
                f"Failed selector: '{selector}'\n"
                f"Updated selector: '{new_selector}'\n"
                f"Keyword: {keyword}\n"
                "Click OK to confirm and save locator.\n"
                "Or click Cancel to keep updating."
            )

            if result:
                break
            else:
                continue
        else:
            break

    return new_selector


def update_source_file(source_file: str, field_name: str, cache_key, keyword: str, new_selector: str):
    # replace keyword with placeholder value if not None
    if keyword:
        new_selector = new_selector.replace(keyword, KEYWORD_PLACEHOLDER)

    path = pathlib.Path(source_file)
    text = path.read_text(encoding="utf-8")

    pattern = (
        rf'(self\.{re.escape(field_name)}\s*=\s*SmartLocator\()'  # part before selector
        rf'(?:self,\s*)?'                                          # optional self argument
        rf'(["\'])(.*?)\2'                                         # selector string
    )
    pattern = rf'self\.{field_name}\s*=.*'
    replacement = f'self.{field_name} = SmartLocator(self, "{new_selector}")'
    new_text, count = re.subn(pattern, replacement, text)

    if  count and text != new_text:
        path.write_text(new_text, encoding="utf-8")
    else:
        messagebox.askokcancel(
            "Locator update failed",
            f"Source file: '{source_file}'\n"
                f"Element name: '{cache_key}'\n"
                f"Fixed locator: {new_selector}\n"
                f"Keyword: {keyword}\n"
                "Click OK or Cancel to terminate record mode."
            )

def system_exit():
    os._exit(1)
import inspect
import os
import re
from conftest import get_current_param_row
import tkinter as tk
from tkinter import messagebox, simpledialog
import pathlib
from utils.web_utils import (get_unique_element_selector,
                             select_element_on_page,
                             get_element_value_or_text)
from utils.class_utils import (get_caller_info,
                               get_function_parameters_index_map,
                               update_value_in_function_call,
                               get_parameter_index_from_function_def,
                               replace_variable_assignment,
                               get_data_provider_names_map,
                               replace_variable_in_data_provider,
                               normalize_args)
from utils.text_utils import replace_line_in_text

KEYWORD_PLACEHOLDER = "#KEYWORD"

# Global cache for runtime locator fixes
FIXED_LOCATORS = {}

# Global cache for runtime locator fixes
FIXED_VALUES = {}

class SmartLocator:
    """
    SmartLocator is a wrapper around Playwright's Locator that provides:
    - Transparent proxying of locator methods (e.g. .fill(), .click()).
    - Self-healing: if a locator fails in record_mode, a popup dialog appears
      to let the user enter a corrected selector (only if GUI available).
    - Runtime caching: corrected locators are stored in a global map.
    - File patching: the page object source file is updated automatically.
    """

    def __init__(self, owner, selector: str):
        self.page = owner.page
        self.config = owner.config
        self.owner = owner
        self.selector = selector
        self.keyword = None

        if not self.selector:
            self.selector = ""

        # Detect field name and source file
        self.field_name, self.source_file = self._get_field_info()

        # Unique key for cache
        self.cache_key = f"{self.owner.__class__.__name__}.{self.field_name}"

        # Reuse fixed locator if already updated this session
        if self.cache_key in FIXED_LOCATORS:
            self.selector = FIXED_LOCATORS[self.cache_key]

    def set_keyword(self, keyword: str):
        """
        Sets dynamic data keyword value that:
        1. Replaces the text match in the element selector string with #KEYWORD# placeholder
        2. Replaces #KEYWORD# placeholder in the element selector string
        This allows to use unique keyword variable as identifier.
        :param keyword: The string value to used instead #KEYWORD# placeholder
        """
        self.keyword = keyword
        # Replace keyword placeholder with keyword value
        if keyword:
            self.selector = self.selector.replace(KEYWORD_PLACEHOLDER, keyword)
            FIXED_LOCATORS[self.cache_key] = self.selector

    def get_keyword(self):
        """
        Gets dynamic data keyword value.
        """
        return self.keyword

    def _get_field_info(self):
        stack = inspect.stack()
        for frame_info in stack:
            if frame_info.code_context:
                line = frame_info.code_context[0].strip()
                if "SmartLocator" in line and "self." in line:
                    match = re.match(r"self\.(\w+)\s*=\s*SmartLocator", line)
                    if match:
                        return match.group(1), frame_info.filename
        return "unknown_field", inspect.getfile(self.owner.__class__)

    def _locator(self):
        if self.selector and self.keyword:
            self.selector = self.selector.replace(KEYWORD_PLACEHOLDER, self.keyword)
        return self.page.locator(self.selector)

    @property
    def locator(self):
        return self._locator()

    def __getattr__(self, item):
        target = getattr(self._locator(), item)

        if callable(target):
            def wrapper(*args, **kwargs):

                if self.config.get("record_mode"):
                    # Normalize so all kwargs become positional
                    args, kwargs = normalize_args(target, *args, **kwargs)
                    # Validate None values and fix them if any
                    args, kwargs = self.validate_none_values(args, kwargs)

                try:
                    return target(*args, **kwargs)
                except Exception as e:
                    error_message = str(e)

                    if self.config.get("record_mode"):

                        if "No node found" in error_message or "Timeout" in error_message:
                            new_locator = self.handle_missing_locator()
                            return getattr(new_locator, item)(*args, **kwargs)
                    raise
            return wrapper
        return target

    def __str__(self):
        if self.selector and self.keyword:
            self.selector = self.selector.replace(KEYWORD_PLACEHOLDER, self.keyword)
        return f"<SmartLocator field='{self.field_name}' selector='{self.selector}'>"

    __repr__ = __str__

    def handle_missing_locator(self):
        root = tk.Tk()
        root.withdraw()

        while True:

            if self.selector.strip() == "":
                self.selector = "Element locator"

            new_selector = simpledialog.askstring(
                "Locator failed",
                f"Locator failed: '{self.selector}'\n"
                f"Element name: '{self.cache_key}'\n"
                f"Keyword: {self.keyword}\n"
                f"Enter new locator and click OK to save it.\n"
                "Or click OK, select element and press Ctrl button.\n"
                "Or click Cancel to terminate record mode.",
                initialvalue=self.selector
            )

            if not new_selector:
                raise RuntimeError("Record mode interrupted by user.")

            if new_selector == self.selector:
                selected_locator = select_element_on_page(self.page)
                new_selector = get_unique_element_selector(selected_locator, self.keyword)

                result = messagebox.askokcancel(
                    "Locator confirmation",
                    f"Locator found: '{new_selector}'\n"
                    f"Element name: '{self.cache_key}'\n"
                    f"Keyword: {self.keyword}\n"
                    "Click OK to confirm and save locator.\n"
                    "Or click Cancel to keep updating."
                )

                if result:
                    break
                else:
                    continue

        # Update this instance + cache
        self.selector = new_selector
        FIXED_LOCATORS[self.cache_key] = new_selector

        # Patch source file
        self.update_source_file(new_selector)

        return self.page.locator(new_selector)

    def update_source_file(self, new_selector):
        # replace keyword with placeholder value if not None
        if self.keyword:
            new_selector = new_selector.replace(self.keyword, KEYWORD_PLACEHOLDER)

        path = pathlib.Path(self.source_file)
        text = path.read_text(encoding="utf-8")

        pattern = rf'self\.{self.field_name}\s*=\s*SmartLocator\(.*?\)'
        replacement = f'self.{self.field_name} = SmartLocator(self, "{new_selector}")'
        new_text = re.sub(pattern, replacement, text)

        if text != new_text:
            path.write_text(new_text, encoding="utf-8")
        else:
            print(f"[SmartLocator] Warning: could not patch {self.cache_key} in {path}")


    def validate_none_values(self, args, kwargs):
        args = list(args)

        for i, arg in enumerate(args):
            if arg is None:

                if self.cache_key in FIXED_VALUES:
                    args[i] = FIXED_VALUES[self.cache_key]

                else:
                    args[i] = self.fix_noname_parameter_none_value(i)

        return tuple(args), kwargs

    def fix_noname_parameter_none_value(self, index):
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
                        "Missing valur",
                        f"None parameter in cannot be fixed\n"
                        f"Line number: {lineno}\n"
                        f"Code line: {code}\n"
                        f"Parameter index: {param_index}\n"
                        "Or OK or Cancel to terminate record mode."
                    )
                    raise RuntimeError("Record mode interrupted by user.")

                return self.fix_none_value_in_file(filename, lineno, code, param_index)

            elif in_stack_blok:
                param_index = get_parameter_index_from_function_def(filename, lineno, param_index)


    def fix_none_value_in_file(self, file_path, lineno, code, param_index):

        while True:
            file_name = os.path.basename(file_path)

            new_value = simpledialog.askstring(
                "Missing parameter value",
                f"None parameter in {file_name}:{lineno}\n"
                f"Code line: {code}\n"
                f"Parameter index: {param_index}\n"
                "Enter correct parameter value and click OK.\n"
                "Or click OK, select element value and press Ctrl.\n"
                "Or click Cancel to terminate record mode.",
                initialvalue="Some value"
            )

            if not new_value:
                raise RuntimeError("Record mode interrupted by user.")

            if new_value == "Some value":
                selected_locator = select_element_on_page(self.page)
                new_value = get_element_value_or_text(selected_locator)

                result = messagebox.askokcancel(
                    "Value confirmation",
                    f"Parameter value for {file_name}:{lineno}\n"
                    f"Code line: {code}\n"
                    f"Parameter index: {param_index}\n"
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

        self.update_value_in_source_file(file_path, lineno, param_index, new_value)
        FIXED_VALUES[self.cache_key] = new_value
        return new_value


    def update_value_in_source_file(self, file_path, lineno, param_index, new_value):
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
                                    "Missing valur",
                                    f"None parameter cannot be fixed\n"
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

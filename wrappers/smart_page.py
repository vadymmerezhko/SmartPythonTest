import inspect
import os
from playwright.sync_api import Page
from helpers.placeholder_manager import PlaceholderManager
from helpers.record_mode_helper import (handle_missing_locator,
                                        fix_noname_parameter_value,
                                        update_source_file)
from utils.code_utils import normalize_args

# Global cache for runtime URL or navigation fixes
FIXED_PAGE_PARAMETERS = {}
# Global cache for runtime keyword fixes
FIXED_KEYWORDS = {}
# Global cache for runtime placeholder name fixes
FIXED_PLACEHOLDER_NAMES = {}
# Global cache for runtime placeholder name fixes
FIXED_PLACEHOLDER_VALUES = {}
# Global cache for runtime page selector fixes
FIXED_PAGE_SELECTORS = {}
PAGE_URL = "page url"
SELECTOR = "selector"
FRAME_URL = "frame url"
FRAME_NAME = "frame name"
KEYWORD_TYPE = "keyword"
PLACEHOLDER_NAME_TYPE = "placeholder name"
PLACEHOLDER_VALUE_TYPE = "placeholder value"
UNSET_VALUE = '=UNSET_VALUE='

class SmartPage:
    """
    SmartPage is a wrapper around Playwright's Page that provides:
    - Transparent proxying of page methods (e.g. .goto(), .fill(), .click()).
    - Self-healing: if navigation or selector fails in record_mode, user can fix it interactively.
    - Placeholder management for dynamic URLs and form data.
    - Runtime caching of fixed values and updated navigation URLs.
    """

    def __init__(self, page: Page, config: dict):
        self.page = page
        self.config = config
        self.placeholder_manager = PlaceholderManager(config)
        self.keyword = None

        # Detect class name and file path for caching
        self.source_file = inspect.getfile(self.__class__)
        self.class_name = self.__class__.__name__
        self.cache_key = f"{self.class_name}@{os.path.basename(self.source_file)}"

    def add_placeholder(self, name: str, value = UNSET_VALUE):

        if not name:
            name = self._validate_placeholder_name(name)

        if not value:
            value = self._validate_placeholder_value(value)
        elif value == UNSET_VALUE:
            value = None

        self.placeholder_manager.add_placeholder(name, value)

    def remove_placeholder(self, name: str):
        self.placeholder_manager.remove_placeholder(name)

    def set_keyword(self, keyword: str):
        self.keyword = keyword
        self._validate_keyword_value()

    def get_keyword(self):
        return self.keyword

    def clear_keyword(self):
        self.keyword = None

    def __getattr__(self, item):
        target = getattr(self.page, item)

        if callable(target):
            def wrapper(*args, **kwargs):
                args, kwargs = normalize_args(target, *args, **kwargs)
                args, kwargs = self._validate_arguments(item, args, kwargs)
                args, kwargs = self._replace_placeholders(args, kwargs)

                try:
                    return target(*args, **kwargs)

                except Exception as e:
                    # Handle page parameter error
                    args, kwargs = self._handle_error(e, item, args, kwargs)

                    return target(*args, **kwargs)

            return wrapper
        return target

    def _replace_placeholders(self, args, kwargs):
        args = list(args)
        for i, arg in enumerate(args):
            if isinstance(arg, str):
                args[i] = self.placeholder_manager.replace_placeholders_with_values(arg)

        for k, v in kwargs.items():
            if isinstance(v, str):
                kwargs[k] = self.placeholder_manager.replace_placeholders_with_values(v)

        return tuple(args), kwargs

    def _validate_keyword_value(self):

        if not self.keyword:
            if self.cache_key in FIXED_KEYWORDS:
                self.keyword = FIXED_KEYWORDS[self.cache_key][1]
            else :
                # Fix keyword None or empty value in record mode
                update = fix_noname_parameter_value(
                    KEYWORD_TYPE, self.page,0, str(self.keyword), self.placeholder_manager)
                FIXED_KEYWORDS[self.cache_key] = update
                self.keyword = update[1]

    def _validate_placeholder_name(self, name: str):
        fixed_name = None

        if not name:
            if self.cache_key in FIXED_PLACEHOLDER_NAMES:
                fixed_name = FIXED_PLACEHOLDER_NAMES[self.cache_key][1]
            else :
                # Fix placeholder name None or empty value in record mode
                name_update = fix_noname_parameter_value(
                    PLACEHOLDER_NAME_TYPE, self.page,0, str(name), self.placeholder_manager)
                FIXED_PLACEHOLDER_NAMES[self.cache_key] = name_update
                fixed_name = name_update[1]

        return fixed_name

    def _validate_placeholder_value(self, value: str):
        fixed_value = None

        if not value:
            if self.cache_key in FIXED_PLACEHOLDER_VALUES:
                fixed_value = FIXED_PLACEHOLDER_VALUES[self.cache_key][1]
            else:
                # Fix placeholder value None or empty value in record mode
                name_update = fix_noname_parameter_value(
                    PLACEHOLDER_NAME_TYPE, self.page, 1, str(value), self.placeholder_manager)
                FIXED_PLACEHOLDER_VALUES[self.cache_key] = name_update
                fixed_value = name_update[1]

        return fixed_value

    def __str__(self):
        return f"<SmartPage {self.__class__.__name__}>"

    def _validate_arguments(self, item, args, kwargs) -> tuple:
        args = list(args)

        if item in "goto":
            parameter_type = PAGE_URL
        elif item in "frame":
            parameter_type = f"{FRAME_NAME} or {FRAME_URL}"
        else:
            parameter_type = SELECTOR

        for i, arg in enumerate(args):
            fixed_value = args[i]

            if self.config.get("record_mode"):
                if arg is None:
                    if self.cache_key in FIXED_PAGE_PARAMETERS:
                        fixed_value = FIXED_PAGE_PARAMETERS[self.cache_key][1]
                    else:
                        update = fix_noname_parameter_value(
                            parameter_type, self.page, i,"None", self.placeholder_manager)
                        FIXED_PAGE_PARAMETERS[self.cache_key] = update
                        fixed_value = update[1]

            if isinstance(args[i], str):
                fixed_value = self.placeholder_manager.replace_placeholders_with_values(fixed_value)

            args[i] = fixed_value
            print(f"Fixed value: {args[i]}")

        return tuple(args), kwargs

    def _fix_selector(self) -> str:
        new_selector = handle_missing_locator(
            self.page, self.cache_key, str(self.selector), self.keyword)
        update_source_file(
            self.source_file, self.field_name, self.cache_key, self.keyword, new_selector)
        # Update this instance + cache
        FIXED_PAGE_SELECTORS[self.cache_key] = new_selector

        return new_selector

    def _fix_parameter(self, item: str, parameter: str):
        parameter_type = None

        if item == "goto":
            parameter_type = PAGE_URL

        elif item == "frame":

            if parameter.strip().startswith(("http", "/", "**")):
                parameter_type = FRAME_URL
            else:
                parameter_type = FRAME_NAME

        update = fix_noname_parameter_value(
            parameter_type, self.page, 0, parameter,
            self.placeholder_manager)
        new_value = update[1]

        if isinstance(new_value, str):
            new_value = (self.placeholder_manager.
                         replace_placeholders_with_values(new_value))

        FIXED_PAGE_PARAMETERS[self.cache_key] = update
        return  new_value

    def _handle_error(self, e: Exception, item: str, args, kwargs):

        # Raise exception for methods without parameters like page.reload()
        if len(args) == 0:
            raise e

        if self.config.get("record_mode") and args and isinstance(args[0], str):
            # Fix parameter for page.goto() and page.frame() methods
            if item in ["goto"] or item in ["frame"]:
                # Fix page parameter value
                new_value = self._fix_parameter(item, args[0])
                args = args[:0] + (new_value,) + args[1:]
                # Retry with fixed parameters or element selector
                args, kwargs = self._replace_placeholders(args, kwargs)

        return args, kwargs

    __repr__ = __str__

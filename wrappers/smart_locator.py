import inspect
import re

from playwright.sync_api import Locator

from common.constnts import KEYWORD_PLACEHOLDER
from helpers.record_mode_helper import (fix_noname_parameter_value,
                                        handle_missing_locator,
                                        update_source_file)
from utils.code_utils import normalize_args


PARAMETER_TYPE = "input"

# Global cache for runtime locator fixes
FIXED_SELECTORS = {}
# Global cache for runtime parameter None value fixes
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

    def __init__(self, owner, selector):
        self.page = owner.page
        self.config = owner.config
        self.owner = owner
        self.selector = str(selector)
        self.placeholder_manager = owner.placeholder_manager

        # Detect field name and source file
        self.field_name, self.source_file = self._get_field_info()

        # Unique key for cache
        self.cache_key = f"{self.owner.__class__.__name__}.{self.field_name}"

        # Reuse fixed locator if already updated this session
        if self.cache_key in FIXED_SELECTORS:
            self.selector = FIXED_SELECTORS[self.cache_key]

    # Sets range slider value
    def set_range_value(self, value):
        self.evaluate(f"el => el.value = {value}")

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
        keyword = self.owner.keyword

        if self.selector and keyword:
            self.selector = self.selector.replace(KEYWORD_PLACEHOLDER, keyword)
        return self.page.locator(self.selector)

    @property
    def locator(self):
        return self._locator()

    def __getattr__(self, item):
        target = getattr(self._locator(), item)

        if callable(target):
            def wrapper(*args, **kwargs):

                # Normalize so all kwargs become positional
                args, kwargs = normalize_args(target, *args, **kwargs)
                # Validate None values and fix them if any
                args, kwargs = self.validate_arguments(args, kwargs)

                try:
                    return target(*args, **kwargs)
                except Exception as e:
                    error_message = str(e)

                    if self.config.get("record_mode"):

                        if ("No node found" in error_message or
                                "Timeout" in error_message or
                                "Unexpected token" in error_message):
                            new_locator = self.fix_locator()
                            return getattr(new_locator, item)(*args, **kwargs)
                    raise
            return wrapper
        return target

    def __str__(self):
        keyword = self.get_keyword()

        if self.selector and keyword:
            self.selector = self.selector.replace(KEYWORD_PLACEHOLDER, keyword)
        return f"<SmartLocator field='{self.field_name}' selector='{self.selector}'>"

    __repr__ = __str__

    def fix_locator(self) -> Locator:
        keyword = self.owner.get_keyword()

        new_selector = handle_missing_locator(
            self.page, self.cache_key, str(self.selector), keyword)
        update_source_file(
            self.source_file, self.field_name, self.cache_key, keyword, new_selector)
        new_locator = self.page.locator(new_selector)
        # Update this instance + cache
        FIXED_SELECTORS[self.cache_key] = new_selector

        return new_locator

    def validate_arguments(self, args, kwargs) -> tuple:
        args = list(args)

        for i, arg in enumerate(args):

            if self.config.get("record_mode"):

                if arg is None:

                    if self.cache_key in FIXED_VALUES:
                        fixed_value = FIXED_VALUES[self.cache_key][1]
                        args[i] = fixed_value
                    else:
                        update = fix_noname_parameter_value(
                            PARAMETER_TYPE, self.page, i,"None", self.placeholder_manager)
                        FIXED_VALUES[self.cache_key] = update
                        args[i] = update[1]

            if isinstance(args[i], str):
                args[i] = self.placeholder_manager.replace_placeholders_with_values(args[i])

        return tuple(args), kwargs


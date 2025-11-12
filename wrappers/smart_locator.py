import inspect
import re
import time
from playwright.sync_api import Locator
from common.constnts import KEYWORD_PLACEHOLDER
from helpers.record_mode_helper import (fix_noname_parameter_value,
                                        handle_missing_locator,
                                        update_source_file)
from utils.code_utils import normalize_args
from utils.web_utils import highlight_element, reset_element_style


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
                args, kwargs = self._validate_arguments(args, kwargs)
                # Validate if selector is None or empty
                locator = self._validate_locator(self._locator())
                element_style = None
                failed = False

                try:
                    element_style = self._highlight_element_with_delay()
                    return getattr(locator, item)(*args, **kwargs)
                except Exception:
                    failed = True
                    new_locator, args, kwargs = self._handle_error(args, kwargs)
                    return getattr(new_locator, item)(*args, **kwargs)
                finally:
                    if not failed:
                        self._restore_element_style(element_style)
            return wrapper
        return target

    def __str__(self):
        keyword = self.get_keyword()

        if self.selector and keyword:
            self.selector = self.selector.replace(KEYWORD_PLACEHOLDER, keyword)
        return f"<SmartLocator field='{self.field_name}' selector='{self.selector}'>"

    __repr__ = __str__

    def _fix_locator(self) -> Locator:
        keyword = self.owner.get_keyword()

        new_selector = handle_missing_locator(
            self.page, self.cache_key, str(self.selector), keyword)
        update_source_file(
            self.source_file, self.field_name, self.cache_key, keyword, new_selector)
        new_locator = self.page.locator(new_selector)
        # Update this instance + cache
        FIXED_SELECTORS[self.cache_key] = new_selector

        return new_locator

    def _validate_arguments(self, args, kwargs) -> tuple:
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

    def _handle_error(self, args, kwargs):
        new_locator = None

        if self.config.get("record_mode"):
            try:
                count = self.page.locator(self.selector).count()
            except Exception:
                count = 0
            # Fix locator
            if count == 0:
                new_locator = self._fix_locator()

            # Fix parameter
            elif args:
                new_locator = self._locator()
                if args:
                    update = fix_noname_parameter_value(
                        PARAMETER_TYPE, self.page, 0, str(args[0]),
                        self.placeholder_manager)
                    new_value = update[1]
                    new_value = (self.placeholder_manager.
                                 replace_placeholders_with_values(new_value))
                    FIXED_VALUES[self.cache_key] = update
                    args = args[:0] + (new_value,) + args[1:]

        return new_locator, args, kwargs

    def _validate_locator(self, locator):

        if self.config.get("record_mode"):

            if not self.selector or self.selector == "None":
                return self._fix_locator()

        return locator

    def _highlight_element_with_delay(self):
        step_delay_milliseconds = self.config.get("step_delay")

        try:
            step_delay_seconds = float(step_delay_milliseconds) / 1000.0
        except (TypeError, ValueError):
            step_delay_seconds = 0.0

        if self.config.get("highlight"):
            element_style = highlight_element(self._locator())
            time.sleep(step_delay_seconds)
            return element_style

        elif step_delay_seconds > 0.0:
            time.sleep(step_delay_seconds)

    def _restore_element_style(self, element_style):

        if self.config.get("highlight") and self.page.locator(self.selector).count() > 0:
            if not element_style:
                reset_element_style(self._locator(), element_style)

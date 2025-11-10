from playwright.sync_api import expect as pw_expect, Page, Locator, APIResponse
from helpers.record_mode_helper import fix_noname_parameter_value
from utils.code_utils import normalize_args
from wrappers.smart_locator import SmartLocator

EXPECTED_TYPE = "expected"
# Global cache for runtime expected value fixes
FIXED_EXPECTS = {}


class SmartExpect:
    def __init__(self, actual):
        self._smart_locator = None
        if isinstance(actual, SmartLocator):
            self.page = actual.page
            self._smart_locator = actual
            self.cache_key = self._smart_locator.cache_key
            self.placeholder_manager = self._smart_locator.placeholder_manager
            unwrapped = actual.locator
        elif isinstance(actual, Locator):
            self.page = actual.page
            unwrapped = actual
        elif isinstance(actual, Page):
            self.page = actual
            unwrapped = actual
        elif isinstance(actual, APIResponse):
            self.page = None
            unwrapped = actual
        else:
            raise ValueError(f"Unsupported type: {type(actual)}")

        self._inner = pw_expect(unwrapped)

    def __getattr__(self, item):
        target = getattr(self._inner, item)

        if callable(target) and item.startswith("to_"):
            def wrapper(*args, **kwargs):
                nonlocal target

                # Attempt recovery if SmartLocator is available
                if self._smart_locator:

                    try:
                        args, kwargs = normalize_args(target, *args, **kwargs)
                        args, kwargs = self._validate_arguments(args, kwargs)

                        target = getattr(self._inner, item)
                        return target(*args, **kwargs)

                    except Exception as e:
                        target, args, kwargs = self._handle_error(item, target, args, kwargs, e)
                        # Retry with fixed expected value
                        return target(*args, **kwargs)
            return wrapper
        return target

    def _validate_arguments(self, args, kwargs):
        args = list(args)

        for i, arg in enumerate(args):

            if self._smart_locator.config.get("record_mode"):

                if self.cache_key in FIXED_EXPECTS:
                    args[i] = FIXED_EXPECTS[self.cache_key][1]
                else:
                    if arg is None:
                        update = fix_noname_parameter_value(
                            EXPECTED_TYPE,self.page,0,"None",self.placeholder_manager)
                        new_value = update[1]
                        FIXED_EXPECTS[self.cache_key] = update
                        args[i] = new_value

            if isinstance(args[i], str):
                args[i] = self.placeholder_manager.replace_placeholders_with_values(args[i])

        return tuple(args), kwargs

    def _handle_error(self, item: str, target, args, kwargs, e: Exception):
        error_message = str(e)

        if self._smart_locator.config.get("record_mode"):
            try:
                count = self.page.locator(self._smart_locator.selector).count()
            except Exception:
                count = 0

            if count == 0:
                fixed_locator = self._smart_locator._validate_locator()
                self._inner = pw_expect(fixed_locator)
                target = getattr(self._inner, item)

            elif isinstance(args[0], str):
                # Fix expected value
                if args:
                    update = fix_noname_parameter_value(
                        EXPECTED_TYPE, self.page, 0, str(args[0]),
                        self.placeholder_manager)
                    new_value = update[1]
                    new_value = (self.placeholder_manager.
                                 replace_placeholders_with_values(new_value))

                    FIXED_EXPECTS[self.cache_key] = update
                    args = args[:0] + (new_value,) + args[1:]

        return target, args, kwargs

    def __dir__(self):
        return dir(self._inner)

# ---------------- helpers ---------------- #

def expect(actual):
    """Public entry point: works with SmartLocator or native Playwright objects."""
    return SmartExpect(actual)

from playwright.sync_api import expect as pw_expect, Page, Locator, APIResponse
from helpers.record_mode_helper import fix_noname_parameter_value
from utils.code_utils import normalize_args
from wrappers.smart_locator import SmartLocator

EXPECTED_TYPE = "expected"
# Global cache for runtime expected value fixes
FIXED_EXPECTS = {}


class SmartExpectProxy:
    def __init__(self, actual):
        self._smart_locator = None
        if isinstance(actual, SmartLocator):
            self.page = actual.page
            self._smart_locator = actual
            self.cache_key = self._smart_locator.cache_key
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
                        if self._smart_locator.config.get("record_mode"):
                            args, kwargs = normalize_args(target, *args, **kwargs)
                            args, kwargs = self.validate_arguments(args, kwargs)

                        target = getattr(self._inner, item)
                        return target(*args, **kwargs)

                    except Exception as e:
                        error_message = str(e)
                        print(f"\nERROR: {error_message}")

                        if self._smart_locator.config.get("record_mode"):
                            try:
                                count = self.page.locator(self._smart_locator.selector).count()
                            except Exception:
                                count = 0

                            if count == 0:
                                fixed_locator = self._smart_locator.fix_locator()
                                self._inner = pw_expect(fixed_locator)
                                target = getattr(self._inner, item)
                                # Retry with fixed locator
                                return target(*args, **kwargs)

                            if "Locator expected" in error_message:
                                print("Expectation failed")
                                # Fix expected value
                                if args:
                                    new_value = fix_noname_parameter_value(
                                        EXPECTED_TYPE, self.page, 0, str(args[0]))
                                    FIXED_EXPECTS[self.cache_key] = new_value
                                    args = args[:0] + (new_value,) + args[1:]
                                    # Retry with fixed expected value
                                    return target(*args, **kwargs)
                        raise
            return wrapper
        return target

    def validate_arguments(self, args, kwargs):
        args = list(args)

        for i, arg in enumerate(args):

            if self.cache_key in FIXED_EXPECTS:
                args[i] = FIXED_EXPECTS[self.cache_key]
            else:
                if arg is None:
                    new_value = fix_noname_parameter_value(EXPECTED_TYPE, self.page, 0, "None")
                    FIXED_EXPECTS[self.cache_key] = new_value
                    args[i] = new_value

        return tuple(args), kwargs

    def __dir__(self):
        return dir(self._inner)

# ---------------- helpers ---------------- #

def expect(actual):
    """Public entry point: works with SmartLocator or native Playwright objects."""
    return SmartExpectProxy(actual)

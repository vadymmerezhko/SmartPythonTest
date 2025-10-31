from playwright.sync_api import expect as pw_expect, Page, Locator, APIResponse
from helpers.code_update_helper import fix_noname_parameter_none_value
from wrappers.smart_locator import SmartLocator

EXPECTED_TYPE = "expected"

# Global cache for runtime expected value fixes
FIXED_EXPECTS = {}


class SmartExpectProxy:
    def __init__(self, actual):
        self._smart_locator = None
        self.page = None

        if isinstance(actual, SmartLocator):
            self.page = actual.page
            self._smart_locator = actual
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

        # Safe cache key (owner/field_name not always available)
        self.cache_key = f"{id(actual)}"

        self._inner = pw_expect(unwrapped)

    def __getattr__(self, item):
        target = getattr(self._inner, item)

        if callable(target) and item.startswith("to_"):
            def wrapper(*args, **kwargs):
                # Attempt recovery if SmartLocator is available
                if self._smart_locator:
                    try:
                        return target(*args, **kwargs)
                    except Exception as e:
                        if self._smart_locator.config.get("record_mode"):
                            msg = str(e)

                            # Retry with fixed locator
                            if "No node found" in msg or "Timeout" in msg:
                                fixed_locator = self._smart_locator.fix_locator()
                                self._inner = pw_expect(fixed_locator)
                                target2 = getattr(self._inner, item)
                                return target2(*args, **kwargs)

                            # Retry with fixed expected value
                            if args and args[0] is None:
                                new_value = fix_noname_parameter_none_value(EXPECTED_TYPE, self.page, 0)
                                FIXED_EXPECTS[self.cache_key] = new_value
                                return target(new_value, **kwargs)
                        raise
                else:
                    return target(*args, **kwargs)
            return wrapper
        return target

    def validate_expected_value(self, value):
        if value is None:
            if self.cache_key in FIXED_EXPECTS:
                return FIXED_EXPECTS[self.cache_key]
            new_value = fix_noname_parameter_none_value(EXPECTED_TYPE, self.page, 0)
            FIXED_EXPECTS[self.cache_key] = new_value
            return new_value
        return value

    def __dir__(self):
        return dir(self._inner)


# ---------------- helpers ---------------- #

def expect(actual):
    """Public entry point: works with SmartLocator or native Playwright objects."""
    return SmartExpectProxy(actual)

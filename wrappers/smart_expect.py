from playwright.sync_api import expect as playwright_expect
from wrappers.smart_locator import SmartLocator


def expect(target):
    """
    SmartExpect wrapper around Playwright's expect().
    - If target is a SmartLocator, unwrap to its .locator
    - Otherwise, pass through directly
    """
    if isinstance(target, SmartLocator):
        return playwright_expect(target.locator)
    return playwright_expect(target)

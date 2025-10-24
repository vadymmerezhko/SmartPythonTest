import os
from playwright.sync_api import Page, Locator

# Try GUI-dependent imports (fail gracefully in CI)
try:
    import pyautogui
    import pygetwindow as gw
    GUI_AVAILABLE = True
except Exception:
    GUI_AVAILABLE = False

    # Safe stubs so import doesn't crash in CI
    class _Stub:
        def __getattr__(self, item):
            raise RuntimeError(f"{item} is not available in headless environment")

    pyautogui = _Stub()
    gw = _Stub()


def get_hovered_element_locator(page: Page):
    """
    Returns a Playwright locator for the innermost element currently hovered by the mouse cursor.
    Uses :hover chain to ensure we don't accidentally select <body> or a container.

    Raises:
        RuntimeError if GUI is not available (e.g. in GitHub Actions CI).
    """
    if not GUI_AVAILABLE:
        raise RuntimeError("get_hovered_element_locator requires GUI, not available in CI")

    selector = page.evaluate("""
        () => {
            const hovered = document.querySelectorAll(':hover');
            if (!hovered || hovered.length === 0) return null;

            const el = hovered[hovered.length - 1]; // innermost hovered element

            let sel = el.tagName.toLowerCase();
            if (el.id) sel += "#" + el.id;
            if (el.className) sel += "." + el.className.toString().replace(/\\s+/g, ".");
            return sel;
        }
    """)

    if not selector:
        raise RuntimeError("No element is currently hovered")

    return page.locator(selector)


def highlight_element(locator: Locator):
    """
    Highlights an element by adding a 2px solid red border.
    Returns the element's original 'style' attribute so it can be restored later.
    """
    original_style = locator.evaluate("el => el.getAttribute('style')")
    locator.evaluate(
        "el => el.setAttribute('style', (el.getAttribute('style') || '') + '; border: 2px solid red !important;')"
    )
    return original_style


def reset_element_style(locator: Locator, original_style: str):
    """
    Restores an element's style attribute to its original value.
    Args:
        locator: The Playwright Locator for the element.
        original_style: The style string returned from highlight_element().
    """
    if original_style is None:
        locator.evaluate("el => el.removeAttribute('style')")
    else:
        locator.evaluate(f"el => el.setAttribute('style', `{original_style}`)")


def get_unique_css_selector(locator: Locator) -> str | None:
    """
    Generate a unique CSS selector string for a Playwright Locator element.
    Priority: id > name > role > class > tag + nth-of-type.
    Returns None if uniqueness cannot be guaranteed.
    """
    element_info = locator.evaluate("""el => {
        if (!el) return null;

        function escapeCss(s) {
            return s.replace(/([ !"#$%&'()*+,.\/:;<=>?@[\\]^`{|}~])/g, '\\\\$1');
        }

        const tag = el.tagName.toLowerCase();
        const attrs = ["id", "name", "role", "data-testid", "aria-label", "alt", "title"];

        for (const attr of attrs) {
            const val = el.getAttribute(attr);
            if (val) {
                const sel = (attr === "id")
                    ? `#${escapeCss(val)}`
                    : `${tag}[${attr}="${escapeCss(val)}"]`;
                if (document.querySelectorAll(sel).length === 1) {
                    return sel;
                }
            }
        }

        if (el.classList.length > 0 && el.classList.length <= 2) {
            const sel = tag + '.' + [...el.classList].map(c => escapeCss(c)).join('.');
            if (document.querySelectorAll(sel).length === 1) return sel;
        }

        const parent = el.parentElement;
        if (parent) {
            const children = Array.from(parent.children).filter(c => c.tagName === el.tagName);
            const idx = children.indexOf(el);
            if (idx >= 0) {
                const sel = `${tag}:nth-of-type(${idx+1})`;
                if (document.querySelectorAll(sel).length === 1) return sel;
            }
        }

        return null;
    }""")

    return element_info


def compare_locators_geometry(locator1: Locator, locator2: Locator, tolerance: float = 0.5) -> bool:
    """
    Compare two locators' position (x, y) and size (width, height).
    Returns True if all values are equal within the given tolerance.
    """
    if locator1 is None or locator2 is None:
        return False

    box1 = locator1.bounding_box()
    box2 = locator2.bounding_box()

    if not box1 or not box2:
        raise ValueError("One or both locators are not visible, bounding_box() returned None")

    for key in ["x", "y", "width", "height"]:
        if abs(box1[key] - box2[key]) > tolerance:
            return False

    return True

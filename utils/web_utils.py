import time
import pyautogui
from pynput import keyboard
import utils.keyboard_utils as ku
from playwright.sync_api import Page, Locator


def get_hovered_element_locator(page: Page):
    """
    Returns a Playwright locator for the innermost element currently hovered by the mouse cursor.
    Uses :hover chain to ensure we don't accidentally select <body> or a container.
    """
    selector = page.evaluate(r"""
        () => {
            const hovered = document.querySelectorAll(':hover');
            if (!hovered || hovered.length === 0) return null;

            const el = hovered[hovered.length - 1]; // innermost hovered element

            let sel = el.tagName.toLowerCase();
            if (el.id) sel += "#" + el.id;
            if (el.className) sel += "." + el.className.toString().replace(/\s+/g, ".");
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
    element_info = locator.evaluate(r"""el => {
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

def select_element_on_page(page):
    """
    Continuously watches the currently hovered element on the page,
    highlights it, and waits for user input to confirm or cancel.

    Workflow:
    1. Tracks the locator under the mouse cursor (using :hover).
    2. If the hovered element changes:
       - Removes highlight from the old element.
       - Applies a red border highlight to the new element.
    3. Waits for keyboard input:
       - ESC → cancels the selection and returns None.
       - CTRL (left or right) → confirms the currently highlighted element and returns it.
    4. Keeps looping until the user presses one of the above keys.

    Args:
        page (Page): Playwright Page object to interact with the DOM.

    Returns:
        Locator | None:
            - The Playwright Locator of the confirmed element if CTRL is pressed.
            - None if ESC is pressed or no element is confirmed.

    Notes:
        - This function relies on pynput keyboard events to capture key presses.
        - The highlighted element's original style is restored when the cursor moves.
        - Runs an infinite loop until the user explicitly cancels or confirms selection.
    """
    last_locator = None
    last_original_style = None

    while True:
        try:
            # Get the element currently under the mouse cursor
            selected_locator = get_hovered_element_locator(page)

            # If the hovered element has changed, update highlight
            if not compare_locators_geometry(selected_locator, last_locator):

                if last_locator is not None:
                    reset_element_style(last_locator, last_original_style)

                last_original_style = highlight_element(selected_locator)
                last_locator = selected_locator

            # Small delay to avoid busy loop
            time.sleep(0.1)

            # Check last pressed key
            pressed_key = ku.get_last_pressed_key()

            if pressed_key == keyboard.Key.esc:
                # Cancel selection
                return None

            if pressed_key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                # Confirm current selection
                return selected_locator

        except Exception:
            # If hovering or style reset fails, retry
            continue

    return None


def get_element_value_or_text(locator):
    """
    Safely retrieves the most meaningful textual or value content from a Playwright locator.

    Args:
        locator (Locator): A Playwright Locator pointing to a DOM element.

    Returns:
        str | None:
            - A string containing the element's value or text.
            - An empty string "" if the element exists but has no text/value.
            - None if no method succeeds (e.g. element is detached or not resolvable).
    """
    value = None

    try:
        # For inputs/textareas/selects
        value = locator.input_value()
    except Exception:
        try:
            # For visible textual content
            value = locator.inner_text()
        except Exception:
            try:
                # For raw text content (including invisible text)
                value = locator.text_content()
            except Exception:
                pass

    return value

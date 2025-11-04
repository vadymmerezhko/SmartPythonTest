import time
import pyautogui
from itertools import combinations
from pynput import keyboard
from typing import Optional
import re
import utils.keyboard_utils as ku
from playwright.sync_api import Locator


from playwright.sync_api import Page

def get_hovered_element_locator(page: Page):
    """
    Returns a Playwright locator for the leaf element (no child elements)
    currently under the mouse cursor. It compares bounding boxes (x,y,width,height)
    of all leaf nodes and returns the one that matches the hovered element position.
    """
    selector = page.evaluate(r"""
        () => {
            function getUniqueSelector(el) {
                if (!el) return null;
                if (el.id) return `#${el.id}`;

                let path = [];
                while (el && el.nodeType === 1 && el !== document.body) {
                    let selector = el.nodeName.toLowerCase();

                    if (el.className) {
                        const classes = el.className.toString().trim().split(/\s+/).filter(Boolean);
                        if (classes.length > 0) {
                            selector += '.' + classes.join('.');
                        }
                    }

                    const parent = el.parentNode;
                    if (parent) {
                        const siblings = Array.from(parent.children).filter(
                            sib => sib.nodeName === el.nodeName
                        );
                        if (siblings.length > 1) {
                            const index = siblings.indexOf(el) + 1;
                            selector += `:nth-of-type(${index})`;
                        }
                    }

                    path.unshift(selector);
                    el = el.parentNode;
                }
                return path.join(' > ');
            }

            let hoveredEl = null;
            if (window.__lastMouseEvent) {
                const { clientX: x, clientY: y } = window.__lastMouseEvent;
                hoveredEl = document.elementFromPoint(x, y);
            }
            if (!hoveredEl) {
                const hovered = document.querySelectorAll(':hover');
                if (hovered && hovered.length > 0) {
                    hoveredEl = hovered[hovered.length - 1];
                }
            }
            if (!hoveredEl) return null;

            // Get bounding box of hovered
            const hoveredRect = hoveredEl.getBoundingClientRect();

            // Find all leaf nodes (elements without children)
            const leaves = [];
            const all = document.querySelectorAll('*');
            all.forEach(el => {
                if (!el.children || el.children.length === 0) {
                    const r = el.getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) {
                        leaves.push({el, rect: r});
                    }
                }
            });

            // Find leaf with same position/size as hovered element
            for (const {el, rect} of leaves) {
                if (
                    Math.abs(rect.x - hoveredRect.x) < 1 &&
                    Math.abs(rect.y - hoveredRect.y) < 1 &&
                    Math.abs(rect.width - hoveredRect.width) < 1 &&
                    Math.abs(rect.height - hoveredRect.height) < 1
                ) {
                    return getUniqueSelector(el);
                }
            }

            // fallback to hovered element
            return getUniqueSelector(hoveredEl);
        }
    """)

    if not selector:
        raise RuntimeError("No element found under mouse cursor")

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


def xpath_to_css(xpath: str) -> Optional[str]:
    """
    Very basic XPath -> CSS converter for simple cases:
    - (//tag)[n] -> tag:nth-of-type(n)
    - //tag[@attr='value'] -> tag[attr='value']
    - //* -> *
    This is not a full converter but good enough for Playwright fallbacks.
    """

    # (//tag)[n]
    match = re.match(r"^\(//(\w+)\)\[(\d+)\]$", xpath)
    if match:
        tag, idx = match.groups()
        return f"{tag}:nth-of-type({idx})"

    # //tag[@attr='value']
    match = re.match(r"^//(\w+)\[@([^=]+)='([^']+)'\]$", xpath)
    if match:
        tag, attr, val = match.groups()
        return f"{tag}[{attr}='{val}']"

    # //* -> *
    if xpath.strip() == "//*":
        return "*"

    return None


def css_to_xpath(css: str) -> str:
    """
    Naive CSS → XPath converter for simple selectors.

    Supports:
      - tag[attr='value'][attr2='value2'] → //tag[@attr='value' and @attr2='value2']
      - #id → //*[@id='id']
      - .class → //*[@class='class']
      - tag.class → //tag[@class='class']
      - * → //*

    Args:
        css (str): CSS selector string.

    Returns:
        str: Equivalent XPath string.
    """
    css = css.strip()

    # Handle ID (#id)
    if css.startswith("#"):
        return f"//*[@id='{css[1:]}']"

    # Handle class (.class)
    if css.startswith("."):
        return f"//*[@class='{css[1:]}']"

    # Extract tag name (or * if none)
    tag_match = re.match(r"^([a-zA-Z0-9*]+)", css)
    tag = tag_match.group(1) if tag_match else "*"

    # Extract .class in tag.class
    class_match = re.search(r"\.([a-zA-Z0-9_-]+)", css)
    attr_exprs = []
    if class_match:
        attr_exprs.append(f"@class='{class_match.group(1)}'")

    # Extract attributes [attr='value']
    attrs = re.findall(r"\[([^\]=]+)='([^']+)'\]", css)
    for k, v in attrs:
        attr_exprs.append(f"@{k}='{v}'")

    # Build XPath
    if attr_exprs:
        return f"//{tag}[" + " and ".join(attr_exprs) + "]"
    else:
        return f"//{tag}"


def get_simple_css_selector(locator: Locator) -> str | None:
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
        const attrs = ["id", "data-id", "data-test", "data-testid", "name",
                       "role", "class", "type", "data-role",
                       "aria-label", "alt", "title", "placeholder"];

        for (const attr of attrs) {
            const val = el.getAttribute(attr);
            if (val) {
                const sel = (attr === "id")
                    ? `#${escapeCss(val)}`
                    : `${tag}[${attr}='${escapeCss(val)}']`;
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


def get_complex_css_selector(locator: Locator) -> str | None:
    """
    Generate a CSS selector string for a Playwright Locator element,
    starting from:
      1. tag only
      2. tag + 1 attribute
      3. tag + 2 attributes
      ...
    Until a unique selector is found.

    Attributes considered (in order):
        class, role, type, tabindex, accesskey,
        draggable, spellcheck, translate, contenteditable,
        autocapitalize, enterkeyhint, required, pattern,
        data-role, data-user, aria-labelledby, aria-required

    Returns:
        str | None: Unique selector string if found, else None.
    """

    attrs_to_check = [
        "class", "role", "data-role", "type", "tabindex", "accesskey",
        "pattern", "draggable", "spellcheck", "translate", "contenteditable",
        "autocapitalize", "enterkeyhint", "required", "aria-required",
        "data-user", "aria-labelledby"
    ]

    # Extract element tag + available attributes
    element_info = locator.evaluate(f"""el => {{
        if (!el) return null;
        const attrs = {{}};
        for (const a of {attrs_to_check!r}) {{
            const val = el.getAttribute(a);
            if (val) attrs[a] = val;
        }}
        return {{
            tag: el.tagName.toLowerCase(),
            attrs
        }};
    }}""")

    if not element_info:
        return None

    tag = element_info["tag"]
    attrs = element_info["attrs"]

    def escape_css(value: str) -> str:
        return value.replace("'", "\\'")  # escape single quotes

    # --- Step 1: check tag alone
    is_tag_unique = locator.page.evaluate(
        """(sel) => document.querySelectorAll(sel).length === 1""",
        tag
    )
    if is_tag_unique:
        return tag

    keys = list(attrs.keys())

    # --- Step 2+: progressively add attributes
    for r in range(1, len(keys) + 1):  # start from 1 attribute
        for combo in combinations(keys, r):
            parts = [f"[{k}='{escape_css(attrs[k])}']" for k in combo]
            selector = tag + "".join(parts)

            is_unique = locator.page.evaluate(
                """(sel) => document.querySelectorAll(sel).length === 1""",
                selector
            )

            if is_unique:
                return selector

    return None


def get_not_unique_complex_css_selector(locator: Locator) -> Optional[str]:
    """
    Generate a not-unique (may return multiple elements) CSS selector
    for a Playwright Locator element:
      1. Start with the tag name.
      2. Add all available attributes among a predefined set.

    Example: div[class='foo'][data-test='login']
    """

    attrs_to_check = [
        "class", "type", "role", "aria-label", "placeholder",
        "draggable", "spellcheck", "translate", "contenteditable",
        "autocapitalize", "enterkeyhint", "required", "pattern",
        "data-role", "data-user", "aria-labelledby", "aria-required"
    ]

    element_info = locator.evaluate(f"""el => {{
        if (!el) return null;
        const attrs = {{}};
        for (const a of {attrs_to_check!r}) {{
            const val = el.getAttribute(a);
            if (val) attrs[a] = val;
        }}
        return {{
            tag: el.tagName.toLowerCase(),
            attrs
        }};
    }}""")

    if not element_info:
        return None

    tag = element_info["tag"]
    attrs = element_info["attrs"]

    def escape_css(value: str) -> str:
        # Escape quotes for safe CSS
        return value.replace("'", "\\'")

    selector = tag
    for k, v in attrs.items():
        selector += f"[{k}='{escape_css(v)}']"

    return selector



def get_css_selector_by_parent(locator: Locator) -> Optional[str]:
    """
    Generate a CSS selector string for a Locator using a unique parent selector + child tag.

    Algorithm:
      1. Get the tag name of the child element.
      2. Walk up parent elements one by one.
      3. For each parent:
         - Try get_simple_css_selector(parent).
         - If None, try get_complex_css_selector(parent).
         - If still None, try converting parent XPath to CSS.
         - If a unique selector is found, return 'parent_selector > child_tag'.
      4. If no unique parent selector found → return None.

    Returns:
        str | None: CSS selector string if unique, else None.
    """

    # Get child tag name
    element_info = locator.evaluate("""el => {
        if (!el) return null;
        return { tag: el.tagName.toLowerCase() };
    }""")
    if not element_info:
        return None

    child_tag = element_info["tag"]

    # Walk up parents
    current = locator
    while True:
        parent = current.locator("..")
        try:
            parent_tag = parent.evaluate("el => el.tagName.toLowerCase()")
        except Exception:
            break  # no parent

        if not parent_tag:
            break

        # Try simple selector
        sel = get_simple_css_selector(parent)
        if not sel:
            sel = get_complex_css_selector(parent)

        # Try xpath fallback
        if not sel:
            try:
                parent_xpath = parent.evaluate("el => el.xpath")  # fake: Playwright doesn’t expose directly
            except Exception:
                parent_xpath = None
            if parent_xpath:
                sel = xpath_to_css(parent_xpath)

        if sel:
            return f"{sel} > {child_tag}"

        current = parent

    return None


def get_css_selector_by_sibling(locator: Locator) -> Optional[str]:
    """
    Generate a CSS selector string for a Locator using a unique sibling selector.

    Algorithm:
      1. Get the target element's tag name.
      2. Look for previous and next siblings of the element.
      3. For each sibling:
         - Try get_simple_css_selector(sibling).
         - If None, try get_complex_css_selector(sibling).
         - If a unique selector is found:
             - Combine with sibling + adjacent combinator (+ or ~).
             - Return "<sibling_selector> + <child_tag>" or "<sibling_selector> ~ <child_tag>".
      4. If no unique sibling selector found → return None.

    Args:
        locator (Locator): Playwright Locator for the element.

    Returns:
        str | None: Unique CSS selector using sibling relation, else None.
    """

    # Get child tag name
    element_info = locator.evaluate("""el => {
        if (!el) return null;
        return { tag: el.tagName.toLowerCase() };
    }""")
    if not element_info:
        return None

    child_tag = element_info["tag"]

    # Try previous sibling
    prev_info = locator.evaluate("""el => {
        if (!el || !el.previousElementSibling) return null;
        return {
            tag: el.previousElementSibling.tagName.toLowerCase()
        };
    }""")
    if prev_info:
        sibling = locator.locator("xpath=preceding-sibling::*[1]")
        sib_sel = get_simple_css_selector(sibling) or get_complex_css_selector(sibling)
        if sib_sel:
            candidate = f"{sib_sel} + {child_tag}"
            is_unique = locator.page.evaluate(
                """sel => document.querySelectorAll(sel).length === 1""", candidate
            )
            if is_unique:
                return candidate

    # Try next sibling
    next_info = locator.evaluate("""el => {
        if (!el || !el.nextElementSibling) return null;
        return {
            tag: el.nextElementSibling.tagName.toLowerCase()
        };
    }""")
    if next_info:
        sibling = locator.locator("xpath=following-sibling::*[1]")
        sib_sel = get_simple_css_selector(sibling) or get_complex_css_selector(sibling)
        if sib_sel:
            candidate = f"{sib_sel} + {child_tag}"
            is_unique = locator.page.evaluate(
                """sel => document.querySelectorAll(sel).length === 1""", candidate
            )
            if is_unique:
                return candidate

    return None


def get_xpath_selector_by_text(locator: Locator) -> Optional[str]:
    """
    Build a unique XPath for the given element based on its visible text.
    - If multiple elements share the text, include index: (//tag[predicate])[n]
    - If only one element matches, return simple form: //tag[predicate]
    """

    def _xpath_literal(s: str) -> str:
        """Safely embed text with quotes into XPath."""
        if "'" not in s:
            return f"'{s}'"
        if '"' not in s:
            return f'"{s}"'
        # both quotes exist → concat form
        parts = s.split("'")
        return "concat(" + ", ".join([f"'{p}'" for p in parts[:-1]] + ["\"'\"", f"'{parts[-1]}'"]) + ")"

    info = locator.evaluate(
        """(el) => {
            if (!el) return null;
            const tag = el.tagName.toLowerCase();
            let t = (el.innerText ?? el.textContent ?? "").replace(/\\s+/g, " ").trim();
            return { tag, text: t };
        }"""
    )
    if not info or not info.get("text"):
        return None

    tag = info["tag"]
    text = info["text"]

    payload = locator.evaluate(
        """(el) => {
            const tag = el.tagName.toLowerCase();
            const norm = s => (s ?? "").replace(/\\s+/g, " ").trim();
            const text = norm(el.innerText ?? el.textContent ?? "");

            const all = Array.from(document.getElementsByTagName(tag));

            const exact = all.filter(n => norm(n.innerText ?? n.textContent ?? "") === text);
            const exactIndex = exact.indexOf(el) + 1;
            const exactCount = exact.length;

            const contains = all.filter(n => norm(n.innerText ?? n.textContent ?? "").includes(text));
            const containsIndex = contains.indexOf(el) + 1;
            const containsCount = contains.length;

            return { tag, text, exactCount, exactIndex, containsCount, containsIndex };
        }"""
    )

    if not payload:
        return None

    lit = _xpath_literal(payload["text"])
    t = payload["tag"]

    # exact-text case
    if payload["exactCount"] >= 1 and payload["exactIndex"] >= 1:
        if payload["exactCount"] == 1:
            return f"xpath=//{t}[normalize-space(.)={lit}]"
        return f"xpath=(//{t}[normalize-space(.)={lit}])[{payload['exactIndex']}]"

    # contains-text case
    if payload["containsCount"] >= 1 and payload["containsIndex"] >= 1:
        if payload["containsCount"] == 1:
            return f"xpath=//{t}[contains(normalize-space(.), {lit})]"
        return f"xpath=(//{t}[contains(normalize-space(.), {lit})])[{payload['containsIndex']}]"

    return None


def get_xpath_selector_by_parent_text(locator: Locator) -> Optional[str]:
    """
    Find a unique XPath for an element by climbing up to a parent that has unique text.
    Then return "<parent_xpath>//<child_tag>".
    """

    # Get child tag name once
    child_tag = locator.evaluate("el => el.tagName.toLowerCase()")
    if not child_tag:
        return None

    current = locator
    while True:
        try:
            parent = current.locator("..")
            parent_tag = parent.evaluate("el => el.tagName.toLowerCase()")
        except Exception:
            break  # reached root

        if not parent_tag or parent_tag.lower() == "html":
            break

        # Try to build unique text-based selector for this parent
        parent_xpath = get_xpath_selector_by_text(parent)
        parent_xpath = parent_xpath.replace("xpath=", "")

        if parent_xpath:
            # Combine parent xpath with original child's tag
            candidate = f"{parent_xpath}//{child_tag}"
            count = locator.page.evaluate(
                """(sel) => document.evaluate(sel, document, null,
                    XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null).snapshotLength""",
                candidate,
            )
            if count == 1:
                return "xpath=" + candidate

        current = parent

    return None


def get_complex_xpath_selector_by_index(locator: Locator) -> Optional[str]:
    """
    Generate a unique XPath selector for a Playwright Locator:
      1. Get CSS selector (simple → complex → fallback tag+class).
      2. Convert CSS → XPath.
      3. Add index [n] so that (//xpath)[n] matches exactly this element.
    """
    page = locator.page

    # Step 1: Try simple CSS first
    css_sel = get_simple_css_selector(locator)
    if not css_sel:
        css_sel = get_complex_css_selector(locator)

    # Fallback: tag + classes
    if not css_sel:
        try:
            tag = locator.evaluate("el => el.tagName.toLowerCase()")
            classes = locator.evaluate("el => el.className")

            if tag:
                if classes:
                    css_sel = f"{tag}[class='{classes}']"
                else:
                    css_sel = tag

        except Exception:
            pass

    if not css_sel:
        return None

    # Step 2: Convert CSS → XPath
    base_xpath = "xpath=" + css_to_xpath(css_sel)

    if not base_xpath:
        return None

    # Step 3: Count all matches
    all_matches = page.locator(base_xpath)
    total = all_matches.count()

    if total == 0:
        return None

    # Step 4: Find this element’s index
    for i in range(total):
        xpath_without_prefix = base_xpath.replace("xpath=", "")
        xpath_wit_index = f"xpath=({xpath_without_prefix})[{i + 1}]"

        try:
            if check_locators_geometry_match(locator, page.locator(xpath_wit_index)):
                return xpath_wit_index

        except Exception:
            pass

    return None


def get_xpath_selector_by_other_element_text(locator: Locator, text: str) -> Optional[str]:
    """
    Build an XPath selector for a target element using the text of a sibling
    (or a nearby ancestor’s sibling) as an anchor.

    Strategy:
      1. Look for an element with exact text: //*[normalize-space(text())='text'].
      2. If not unique, fall back to partial match: //*[contains(normalize-space(text()), 'text')].
      3. If still not unique, give up (return None).
      4. Once a unique "other" element is found:
         - If it geometrically matches the target locator, return its XPath.
         - Otherwise, try to combine it with the target’s own structure:
             a. First, check if the target is a child of the text element.
             b. If not, walk up 1–4 parent levels and attempt to form an XPath like:
                xpath=//<other_text_xpath>/../..//<target_xpath>
      5. Return the first XPath that resolves uniquely to the target element.

    Args:
        locator (Locator): Playwright Locator for the target element.
        text (str): Text content of the sibling/anchor element.

    Returns:
        str | None: A valid, unique XPath selector string if found, else None.
    """
    page = locator.page

    # Exact text first
    other_xpath = f"xpath=//*[normalize-space(text())='{text}']"
    count = page.locator(other_xpath).count()

    if count != 1:
        # Check the text is unique
        other_xpath = f"xpath=//*[contains(normalize-space(text()), '{text}')]"
        count = page.locator(other_xpath).count()

        if count != 1:
            return None

    target_css = get_not_unique_complex_css_selector(locator)

    if not target_css:
        return None

    other_locator = page.locator(other_xpath)
    target_xpath = css_to_xpath(target_css)
    other_xpath = other_xpath.replace("xpath=", "")
    target_xpath = target_xpath.replace("xpath=", "")

    # Other element is the same as the target element
    if check_locators_geometry_match(locator, other_locator):
        return other_xpath

    # Check if other-based xpath actually resolves to our locator
    child_xpath = f"{other_xpath}{target_xpath.replace('xpath=', '')}"

    child_locator = page.locator(child_xpath)
    child_count = child_locator.count()

    if child_count == 1 and check_locators_geometry_match(locator, child_locator.first):
        return child_xpath

    current_locator = locator

    while True:

        parent_locator = current_locator.locator("..")
        current_locator = parent_locator

        if not parent_locator:
            return None

        tag = parent_locator.evaluate("el => el.tagName.toLowerCase()")

        if tag == "html":
            return None

        if check_parent_contains_child(parent_locator, locator) and \
            check_parent_contains_child(parent_locator, other_locator):

            parent_css = get_not_unique_complex_css_selector(parent_locator)
            parent_xpath = css_to_xpath(parent_css)
            result_xpath = f"xpath={parent_xpath}[.{other_xpath}]{target_xpath}"
            count = page.locator(result_xpath).count()

            if count == 1:
                return result_xpath


def get_unique_element_selector(locator: Locator, text: str = None) -> str | None:
    """
    Build a unique CSS selector string for the given Playwright Locator.

    The function attempts to generate the most reliable selector in two steps:
    1. It first tries to build a simple CSS selector (usually based on unique `id`
       or a single strong attribute) using `get_simple_css_selector(locator)`.
    2. If a simple selector cannot be generated or is not unique, it falls back
       to `get_complex_css_selector(locator)`, which builds a selector that combines
       multiple attributes (e.g., tag + id + class + data-*).

    Args:
        locator (Locator): A Playwright Locator pointing to the target element.

    Returns:
        str | None: A unique CSS selector string if one can be constructed,
        otherwise None if neither simple nor complex selectors could uniquely
        identify the element.
    """

    if not text:
        selector = get_simple_css_selector(locator)

        if not selector:
            selector = get_complex_css_selector(locator)

        if not selector:
            selector = get_css_selector_by_parent(locator)

        if not selector:
            selector = get_css_selector_by_sibling(locator)

        if not selector:
            selector = get_xpath_selector_by_text(locator)

        if not selector:
            selector = get_xpath_selector_by_parent_text(locator)

        if not selector:
            selector = get_complex_xpath_selector_by_index(locator)
    else:
        selector = get_xpath_selector_by_other_element_text(locator, text)

    return selector


def check_locators_geometry_match(locator1: Locator, locator2: Locator, tolerance: float = 0.5) -> bool:
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

def _contains(parent_box, child_box) -> bool:
    if not parent_box or not child_box:
        return False

    px1, py1 = parent_box["x"], parent_box["y"]
    px2, py2 = px1 + parent_box["width"], py1 + parent_box["height"]

    cx1, cy1 = child_box["x"], child_box["y"]
    cx2, cy2 = cx1 + child_box["width"], cy1 + child_box["height"]

    return (px1 <= cx1 and py1 <= cy1 and
            px2 >= cx2 and py2 >= cy2)


def check_parent_contains_child(parent: Locator, child: Locator) -> bool:
    """
    Compare two locators' position (x, y) and size (width, height).
    Returns True if all values are equal within the given tolerance.
    """
    if parent is None or child is None:
        return False

    parent_box = parent.bounding_box()
    child_box = child.bounding_box()

    if not parent_box or not child_box:
        raise ValueError("One or both locators are not visible, bounding_box() returned None")

    return _contains(parent_box, child_box)


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
            if not check_locators_geometry_match(selected_locator, last_locator):

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
                reset_element_style(last_locator, last_original_style)
                return selected_locator

        except Exception:
            # If hovering or style reset fails, retry
            continue

    reset_element_style(last_locator, last_original_style)
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

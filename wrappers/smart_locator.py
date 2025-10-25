import inspect
import re
import tkinter as tk
from tkinter import simpledialog
import time
import pathlib
import utils.keyboard_utils as ku
from utils.web_utils import (
    get_hovered_element_locator, highlight_element,
    reset_element_style, get_unique_css_selector,
    compare_locators_geometry
)

# Safe import for pynput.keyboard (may fail in headless CI)
try:
    from pynput import keyboard
    GUI_AVAILABLE = True
except Exception:
    GUI_AVAILABLE = False

    # Minimal stub so code can still import in CI
    class _KeyboardStub:
        class Key:
            ctrl_l = "ctrl_l"
            ctrl_r = "ctrl_r"
            esc = "esc"

    keyboard = _KeyboardStub()


# Global cache for runtime locator fixes
FIXED_LOCATORS = {}


class SmartLocator:
    """
    SmartLocator is a wrapper around Playwright's Locator that provides:
    - Transparent proxying of locator methods (e.g. .fill(), .click()).
    - Self-healing: if a locator fails in record_mode, a popup dialog appears
      to let the user enter a corrected selector (only if GUI available).
    - Runtime caching: corrected locators are stored in a global map.
    - File patching: the page object source file is updated automatically.
    """

    def __init__(self, owner, selector: str):
        self.page = owner.page
        self.config = owner.config
        self.owner = owner
        self.selector = selector

        # Detect field name and source file
        self.field_name, self.source_file = self._get_field_info()

        # Unique key for cache
        self.cache_key = f"{self.owner.__class__.__name__}.{self.field_name}"

        # Reuse fixed locator if already updated this session
        if self.cache_key in FIXED_LOCATORS:
            self.selector = FIXED_LOCATORS[self.cache_key]

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
        return self.page.locator(self.selector)

    @property
    def locator(self):
        return self._locator()

    def __getattr__(self, item):
        target = getattr(self._locator(), item)

        if callable(target):
            def wrapper(*args, **kwargs):
                try:
                    return target(*args, **kwargs)
                except Exception:
                    if self.config.get("record_mode") and GUI_AVAILABLE:
                        print(f"[SmartLocator] '{item}' failed for {self.cache_key}, opening dialog...")
                        new_locator = self.handle_missing_locator()
                        return getattr(new_locator, item)(*args, **kwargs)
                    raise
            return wrapper
        return target

    def __str__(self):
        return f"<SmartLocator field='{self.field_name}' selector='{self.selector}'>"

    __repr__ = __str__

    def handle_missing_locator(self):
        if not GUI_AVAILABLE:
            raise RuntimeError("Record mode locator fixing requires GUI, not available in CI")

        root = tk.Tk()
        root.withdraw()
        new_selector = simpledialog.askstring(
            "Locator not found",
            f"Locator '{self.selector}' failed.\n"
            f"Enter new locator for '{self.cache_key}'\n"
            "Or press OK button, select element on the page\n"
            "and press Ctrl button.",
            initialvalue=self.selector
        )

        if new_selector == self.selector:
            new_selector = self.get_element_locator_string(new_selector)

        if not new_selector:
            raise RuntimeError("Record mode interrupted by user.")

        # Update this instance + cache
        self.selector = new_selector
        FIXED_LOCATORS[self.cache_key] = new_selector

        # Patch source file
        self.update_source_file(new_selector)

        print(f"[SmartLocator] Updated {self.cache_key} → {new_selector}")
        return self.page.locator(new_selector)

    def update_source_file(self, new_selector):
        path = pathlib.Path(self.source_file)
        text = path.read_text(encoding="utf-8")

        pattern = rf'self\.{self.field_name}\s*=\s*SmartLocator\(.*?\)'
        replacement = f'self.{self.field_name} = SmartLocator(self, "{new_selector}")'
        new_text = re.sub(pattern, replacement, text)

        if text != new_text:
            path.write_text(new_text, encoding="utf-8")
            print(f"[SmartLocator] File updated: {path} ({self.cache_key} → {new_selector})")
        else:
            print(f"[SmartLocator] Warning: could not patch {self.cache_key} in {path}")

    def get_element_locator_string(self, new_selector):
        if not GUI_AVAILABLE:
            return new_selector

        last_locator = None
        last_original_style = None

        while new_selector == self.selector:
            try:
                selected_locator = get_hovered_element_locator(self.page)
                locator_string = get_unique_css_selector(selected_locator)

                if not compare_locators_geometry(selected_locator, last_locator):

                    if last_locator is not None:
                        reset_element_style(last_locator, last_original_style)
                    last_original_style = highlight_element(selected_locator)
                    last_locator = selected_locator

                time.sleep(0.1)
                pressed_key = ku.get_last_pressed_key()

                if pressed_key == keyboard.Key.esc:
                    return None

                if pressed_key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    if locator_string:
                        new_selector = locator_string
            except Exception:
                continue

        return new_selector

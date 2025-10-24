import inspect
import re
import tkinter as tk
from tkinter import simpledialog
from pynput import keyboard
import time
import utils.keyboard_utils as ku
from utils.web_utils import (get_hovered_element_locator, highlight_element,
                             reset_element_style, get_unique_css_selector,
                             compare_locators_geometry)
import pathlib

# Global cache for runtime locator fixes
# Example: { "LoginPage.username_input": "#user-name" }
FIXED_LOCATORS = {}


class SmartLocator:
    """
    SmartLocator is a wrapper around Playwright's Locator that provides:
    - Transparent proxying of locator methods (e.g. .fill(), .click()).
    - Self-healing: if a locator fails in record_mode, a popup dialog appears
      to let the user enter a corrected selector.
    - Runtime caching: corrected locators are stored in a global map so they
      are reused for the rest of the pytest session.
    - File patching: the page object source file is updated with the new
      locator so future test runs use the corrected value automatically.
    """

    def __init__(self, owner, selector: str):
        """
        Initialize a SmartLocator.

        Args:
            owner: The page object instance that owns this locator.
            selector (str): The initial CSS/XPath selector string.
        """
        self.page = owner.page
        self.config = owner.config
        self.owner = owner
        self.selector = selector

        # Detect field name and source file where SmartLocator is declared
        self.field_name, self.source_file = self._get_field_info()

        # Unique key for global cache (e.g. "LoginPage.username_input")
        self.cache_key = f"{self.owner.__class__.__name__}.{self.field_name}"

        # If locator already fixed in this pytest session, reuse it
        if self.cache_key in FIXED_LOCATORS:
            self.selector = FIXED_LOCATORS[self.cache_key]

    def _get_field_info(self):
        """
        Inspect the call stack to determine:
        - The field name (e.g. "username_input")
        - The source file where this SmartLocator is declared
        """
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
        """
        Return a Playwright Locator object for the current selector.
        Always resolves fresh, so runtime updates are respected.
        """
        return self.page.locator(self.selector)

    @property
    def locator(self):
        """
        Expose the underlying Playwright Locator.
        Useful for Playwright's `expect()` API, e.g.:

            expect(self.username_input.locator).to_be_visible()
        """
        return self._locator()

    def __getattr__(self, item):
        """
        Proxy all unknown attributes/methods to the underlying Locator.
        If a method call fails and record_mode=True, trigger self-healing:
        - Show popup dialog for a new selector.
        - Update runtime, global cache, and source file.
        - Retry the failed method with the new selector.
        """
        target = getattr(self._locator(), item)

        if callable(target):
            def wrapper(*args, **kwargs):
                try:
                    return target(*args, **kwargs)
                except Exception:
                    if self.config.get("record_mode"):
                        print(f"[SmartLocator] '{item}' failed for {self.cache_key}, opening dialog...")
                        new_locator = self.handle_missing_locator()
                        return getattr(new_locator, item)(*args, **kwargs)
                    raise
            return wrapper
        return target

    def __str__(self):
        """Human-readable string representation for debugging."""
        return f"<SmartLocator field='{self.field_name}' selector='{self.selector}'>"

    def __repr__(self):
        """Developer-friendly representation (same as __str__)."""
        return self.__str__()

    def handle_missing_locator(self):
        """
        Called when a locator method fails.
        - Opens a Tkinter input dialog asking for a new selector.
        - Updates runtime instance and global cache.
        - Patches the page object file.
        - Returns a Playwright Locator for the new selector.
        """
        root = tk.Tk()
        root.withdraw()
        new_selector = simpledialog.askstring(
            "Locator not found",
            f"Locator '{self.selector}' failed.\n"
            f"Enter new locator for '{self.cache_key}'\n"
            "Or press OK button, select element on the page\n"
            "and press Ctrl button."
        )

        new_selector = self.get_element_locator_string(new_selector)

        if not new_selector:
            raise RuntimeError("Record mode interrupted by user.")

        # Update this instance
        self.selector = new_selector

        # Save into global cache
        FIXED_LOCATORS[self.cache_key] = new_selector

        # Patch the file for future runs
        self.update_source_file(new_selector)

        print(f"[SmartLocator] Updated {self.cache_key} → {new_selector}")
        return self.page.locator(new_selector)

    def update_source_file(self, new_selector):
        """
        Patch the corresponding page object file, replacing the invalid selector
        with the new one provided by the user.

        Args:
            new_selector (str): The corrected selector string.
        """
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
        """
        Selects element on the screen and returns it's unique string locator
        if input selector string is empty.

        Args:
            new_selector (str): The new selector string entered by user.
        """
        last_locator = None

        while new_selector == "":
            try:
                selected_locator = get_hovered_element_locator(self.page)
                locator_string = get_unique_css_selector(selected_locator)

                # If it's a new element under cursor
                if not compare_locators_geometry(selected_locator, last_locator):

                    if last_locator is not None:
                        reset_element_style(last_locator, last_original_style)

                    last_original_style = highlight_element(selected_locator)
                    last_locator = selected_locator

                time.sleep(0.1)
                pressed_key = ku.get_last_pressed_key()

                if pressed_key == keyboard.Key.esc:
                    return None

                if pressed_key == keyboard.Key.ctrl_l or pressed_key == keyboard.Key.ctrl_r:

                    if locator_string:
                        new_selector = locator_string
            except Exception:
                continue

        return new_selector
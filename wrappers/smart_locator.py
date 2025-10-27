import inspect
import re
import tkinter as tk
from tkinter import messagebox, simpledialog
import pathlib
from utils.web_utils import get_unique_element_selector, select_element_on_page

KEYWORD_PLACEHOLDER = "#KEYWORD"

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
        self.keyword = None

        # Detect field name and source file
        self.field_name, self.source_file = self._get_field_info()

        # Unique key for cache
        self.cache_key = f"{self.owner.__class__.__name__}.{self.field_name}"

        # Reuse fixed locator if already updated this session
        if self.cache_key in FIXED_LOCATORS:
            self.selector = FIXED_LOCATORS[self.cache_key]

    def set_keyword(self, keyword: str):
        """
        Sets dynamic data keyword value that:
        1. Replaces the text match in the element selector string with #KEYWORD# placeholder
        2. Replaces #KEYWORD# placeholder in the element selector string
        This allows to use unique keyword variable as identifier.
        :param keyword: The string value to used instead #KEYWORD# placeholder
        """
        self.keyword = keyword
        # Replace keyword placeholder with keyword value
        if keyword:
            self.selector = self.selector.replace(KEYWORD_PLACEHOLDER, keyword)
            FIXED_LOCATORS[self.cache_key] = self.selector

    def get_keyword(self):
        """
        Gets dynamic data keyword value.
        """
        return self.keyword

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
        if self.selector and self.keyword:
            self.selector = self.selector.replace(KEYWORD_PLACEHOLDER, self.keyword)
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
                    if self.config.get("record_mode"):
                        print(f"[SmartLocator] '{item}' failed for {self.cache_key}, opening dialog...")
                        new_locator = self.handle_missing_locator()
                        return getattr(new_locator, item)(*args, **kwargs)
                    raise
            return wrapper
        return target

    def __str__(self):
        if self.selector and self.keyword:
            self.selector = self.selector.replace(KEYWORD_PLACEHOLDER, self.keyword)
        return f"<SmartLocator field='{self.field_name}' selector='{self.selector}'>"

    __repr__ = __str__

    def handle_missing_locator(self):
        root = tk.Tk()
        root.withdraw()

        while True:

            if self.selector.strip() == "":
                self.selector = "Element locator"

            new_selector = simpledialog.askstring(
                "Locator failed",
                f"Locator failed: '{self.selector}'\n"
                f"Element name: '{self.cache_key}'\n"
                f"Keyword: {self.keyword}\n"
                f"Enter new locator and click OK to save it.\n"
                "Or click OK, select element and press Ctrl button.\n"
                "Or click Cancel to terminate record mode.",
                initialvalue=self.selector
            )

            if not new_selector:
                raise RuntimeError("Record mode interrupted by user.")

            if new_selector == self.selector:
                selected_locator = select_element_on_page(self.page)
                new_selector = get_unique_element_selector(selected_locator, self.keyword)

                result = messagebox.askokcancel(
                    "Locator confirmation",
                    f"Locator found: '{new_selector}'\n"
                    f"Element name: '{self.cache_key}'\n"
                    f"Keyword: {self.keyword}\n"
                    "Click OK to confirm and save locator.\n"
                    "Or click Cancel to keep updating."
                )

                if result:
                    break
                else:
                    continue

        # Update this instance + cache
        self.selector = new_selector
        FIXED_LOCATORS[self.cache_key] = new_selector

        # Patch source file
        self.update_source_file(new_selector)

        print(f"[SmartLocator] Updated {self.cache_key} → {new_selector}")
        return self.page.locator(new_selector)

    def update_source_file(self, new_selector):
        # replace keyword with placeholder value if not None
        if self.keyword:
            new_selector = new_selector.replace(self.keyword, KEYWORD_PLACEHOLDER)

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


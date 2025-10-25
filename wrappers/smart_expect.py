# wrappers/smart_expect.py
import inspect
import pathlib
import re
import tkinter as tk
from tkinter import messagebox, simpledialog
from playwright.sync_api import expect as pw_expect, Page, Locator, APIResponse
from wrappers.smart_locator import SmartLocator
from utils.web_utils import select_element_on_page, get_element_value_or_text

FIXED_EXPECTS = {}


class SmartExpectProxy:
    def __init__(self, actual):
        self._smart_locator = None
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

        self._inner = pw_expect(unwrapped)

    def __getattr__(self, item):
        target = getattr(self._inner, item)

        if callable(target) and item.startswith("to_"):
            def wrapper(*args, **kwargs):
                nonlocal target

                # ---- Step 1: Heal locator first if SmartLocator is invalid ----
                if self._smart_locator:
                    try:
                        count = self._smart_locator.locator.count()
                        if count == 0 and self._smart_locator.config.get("record_mode"):
                            print(f"[SmartExpect] Healing locator in {self._smart_locator.cache_key}...")
                            fixed_locator = self._smart_locator.handle_missing_locator()
                            self._inner = pw_expect(fixed_locator)
                            target = getattr(self._inner, item)
                    except Exception:
                        if self._smart_locator.config.get("record_mode"):
                            print(f"[SmartExpect] Locator resolution failed for {self._smart_locator.cache_key}, healing...")
                            fixed_locator = self._smart_locator.handle_missing_locator()
                            self._inner = pw_expect(fixed_locator)
                            target = getattr(self._inner, item)

                # ---- Step 2: Run assertion, fix expected value if needed ----
                try:
                    return target(*args, **kwargs)
                except AssertionError as e:
                    # --- Extract test file info ---
                    test_frame = None
                    for frame_info in inspect.stack():
                        fname = pathlib.Path(frame_info.filename).resolve()
                        if "site-packages" not in str(fname) and "playwright" not in str(fname):
                            if str(fname).endswith(".py") and (
                                "tests" in str(fname) or "test_" in fname.name
                            ):
                                test_frame = frame_info
                                break
                    if not test_frame:
                        test_frame = inspect.stack()[1]

                    filename = pathlib.Path(test_frame.filename).resolve()
                    line_no = test_frame.lineno
                    lines = filename.read_text(encoding="utf-8").splitlines()

                    if args:
                        expected_value = args[0]

                        cached = FIXED_EXPECTS.get((str(filename), str(expected_value)))
                        if cached:
                            print(f"[SmartExpect] Using cached expected value: {cached}")
                            return target(cached, **kwargs)

                        root = tk.Tk()
                        root.withdraw()

                        while True:
                            new_value = simpledialog.askstring(
                                "Expectation failed",
                                f"Expectation failed in {filename.name}:{line_no}\n"
                                f"Expected: {expected_value}\n"
                                "Enter correct expected value and click OK.\n"
                                "Or click OK, select element value and press Ctrl.\n"
                                "Or click Cancel to terminate record mode.",
                                initialvalue=expected_value
                            )

                            if not new_value:
                                raise RuntimeError("Record mode interrupted by user.")

                            if new_value == expected_value:
                                selected_locator = select_element_on_page(self.page)
                                new_value = get_element_value_or_text(selected_locator)

                                result = messagebox.askokcancel(
                                    "Value confirmation",
                                    f"Expected value found for {filename.name}:{line_no}\n"
                                    f"Expected: {new_value}\n"
                                    "Click OK to confirm and save this value.\n"
                                    "Or click Cancel to retry."
                                )

                                if result:
                                    break
                                else:
                                    new_value = expected_value
                                    continue

                        root.destroy()
                        if not new_value:
                            raise e

                        updated = update_expected_value(
                            filename, lines, line_no, str(expected_value), new_value
                        )
                        if updated:
                            print(f"[SmartExpect] File updated: {updated} ({expected_value} → {new_value})")
                        else:
                            print(f"[SmartExpect] Warning: could not patch {expected_value} in {filename}")

                        FIXED_EXPECTS[(str(filename), str(expected_value))] = new_value
                        return target(new_value, **kwargs)

                    raise
            return wrapper
        return target

    def __dir__(self):
        return dir(self._inner)


# ---------------- helpers ---------------- #

def expect(actual):
    """Public entry point: works with SmartLocator or native Playwright objects."""
    return SmartExpectProxy(actual)


def update_expected_value(filename, lines, line_no, old_value, new_value):
    """Patch inline string, constant, or parametrize row in test file."""
    line_idx = line_no - 1
    if not (0 <= line_idx < len(lines)):
        return None

    line = lines[line_idx]

    # case 1: inline literal
    if f"'{old_value}'" in line or f'"{old_value}"' in line:
        lines[line_idx] = line.replace(f"'{old_value}'", f"'{new_value}'").replace(
            f'"{old_value}"', f"'{new_value}'"
        )
        filename.write_text("\n".join(lines), encoding="utf-8")
        return filename

    # case 2: constant
    const_match = re.search(r"to_have_text\((\w+)\)", line)
    if const_match:
        const_name = const_match.group(1)
        defining_file = find_constant_definition(filename, lines, const_name)
        if defining_file:
            text = defining_file.read_text(encoding="utf-8")
            const_pattern = rf'^{const_name}\s*=\s*["\'].*["\']'
            repl = f"{const_name} = '{new_value}'"
            new_text = re.sub(const_pattern, repl, text, flags=re.MULTILINE)
            defining_file.write_text(new_text, encoding="utf-8")
            return defining_file

    # case 3: parametrize row
    provider_file = patch_parametrize_value(filename, lines, old_value, new_value)
    if provider_file:
        return provider_file

    return None


def patch_parametrize_value(filename, lines, old_value, new_value):
    """Patch pytest parametrize rows with string replacement."""
    inside_block = False
    changed = False
    new_lines = []

    for line in lines:
        if line.strip().startswith("@pytest.mark.parametrize"):
            inside_block = True
            new_lines.append(line)
            continue

        if inside_block:
            if line.strip().startswith("])"):
                inside_block = False
                new_lines.append(line)
                continue

            m = re.match(r"\s*\((.+)\)\s*,?\s*", line)
            if m:
                row_content = m.group(1)
                parts = [p.strip() for p in re.split(r",(?![^()]*\))", row_content)]

                updated_parts = []
                for part in parts:
                    if part.startswith(("'", '"')) and old_value in part.strip("'\""):
                        updated_parts.append(f"'{new_value}'")
                        changed = True
                    else:
                        updated_parts.append(part)

                new_line = "    (" + ", ".join(updated_parts) + "),"
                new_lines.append(new_line)
                continue

        new_lines.append(line)

    if changed:
        filename.write_text("\n".join(new_lines), encoding="utf-8")
        return filename
    return None


def find_constant_definition(test_file, lines, const_name):
    for line in lines:
        if line.strip().startswith(f"{const_name} ="):
            return test_file
    for line in lines:
        if line.strip().startswith("from ") and " import " in line:
            if const_name in line:
                module = line.split("from ")[1].split(" import ")[0].strip()
                mod_path = resolve_module_path(test_file, module)
                if mod_path:
                    return mod_path
    return None


def resolve_module_path(test_file, module):
    root = test_file.parent
    while root.name != "tests" and root != root.parent:
        root = root.parent
    project_root = root.parent

    parts = module.split(".")
    path = project_root.joinpath(*parts)
    if path.with_suffix(".py").exists():
        return path.with_suffix(".py")
    elif path.joinpath("__init__.py").exists():
        return path.joinpath("__init__.py")
    return None

import pytest
from unittest.mock import patch
from enums.update_type import UpdateType

# A minimal dummy placeholder manager for tests
class DummyPlaceholderManager:
    def replace_values_with_placeholders(self, value):
        return value

# -----------------------------
# Tests for fix_value_in_file()
# -----------------------------
@patch("helpers.record_mode_helper.simpledialog.askstring", return_value="fixed_value")
@patch("helpers.record_mode_helper.messagebox.askokcancel", return_value=True)
@patch("helpers.record_mode_helper.select_element_on_page")
@patch("helpers.record_mode_helper.get_element_value_or_text", return_value="fixed_value")
@patch("helpers.record_mode_helper.update_value_in_source_file", return_value=UpdateType.INLINE)
def test_fix_value_in_file_positive(mock_update, mock_get, mock_select, mock_msg, mock_input, tmp_path):
    from helpers.record_mode_helper import fix_value_in_file
    page = object()
    file_path = tmp_path / "test_file.py"
    file_path.write_text("print('Hello')")

    result = fix_value_in_file("locator", page, str(file_path), 10, "code()", 1, "old", DummyPlaceholderManager())

    assert result == (UpdateType.INLINE, "fixed_value")
    mock_input.assert_called_once()
    mock_update.assert_called_once()


# -----------------------------
# Tests for handle_missing_locator()
# -----------------------------
@patch("helpers.record_mode_helper.simpledialog.askstring", return_value="new_selector")
def test_handle_missing_locator_simple(mock_input):
    from helpers.record_mode_helper import handle_missing_locator
    result = handle_missing_locator(page=None, cache_key="btnLogin",
                                    selector="old_sel", keyword="keyword")
    assert result == "new_selector"


# -----------------------------
# Tests for update_source_file()
# -----------------------------
@patch("helpers.record_mode_helper.messagebox.askokcancel")
def test_update_source_file_replaces_selector(mock_msg, tmp_path):
    from helpers.record_mode_helper import update_source_file
    file_path = tmp_path / "page_object.py"
    file_path.write_text('self.button = SmartLocator(self, "old_selector")', encoding="utf-8")

    update_source_file(str(file_path), "button", "button_key", "keyword", "new_selector")

    content = file_path.read_text(encoding="utf-8")
    assert "new_selector" in content
    assert mock_msg.call_count == 0


@patch("helpers.record_mode_helper.messagebox.askokcancel")
def test_update_source_file_no_change_shows_messagebox(mock_msg, tmp_path):
    from helpers.record_mode_helper import update_source_file
    file_path = tmp_path / "page_object.py"
    # line does not match SmartLocator pattern -> should call messagebox
    file_path.write_text("print('no locator here')", encoding="utf-8")

    update_source_file(str(file_path), "button", "button_key", "keyword", "new_selector")

    mock_msg.assert_called_once()

import pytest
from utils.text_utils import replace_line_in_text


def test_replace_middle_line():
    text = "line1\nline2\nline3"
    result = replace_line_in_text(text, 2, "new_line2")
    assert result == "line1\nnew_line2\nline3"


def test_replace_first_line():
    text = "line1\nline2\nline3"
    result = replace_line_in_text(text, 1, "new_first")
    assert result == "new_first\nline2\nline3"


def test_replace_last_line():
    text = "line1\nline2\nline3"
    result = replace_line_in_text(text, 3, "new_last")
    assert result == "line1\nline2\nnew_last"


def test_single_line_text():
    text = "onlyline"
    result = replace_line_in_text(text, 1, "newline")
    assert result == "newline"


def test_line_number_out_of_range_raises():
    text = "line1\nline2"
    with pytest.raises(IndexError):
        replace_line_in_text(text, 5, "oops")


def test_preserve_number_of_lines():
    text = "line1\nline2\nline3\n"
    result = replace_line_in_text(text.strip(), 2, "xxx")
    # After replacing, should still have 3 lines
    assert result.count("\n") == 2

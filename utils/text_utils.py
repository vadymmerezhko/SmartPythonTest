def replace_line_in_text(text: str, lineno: int, new_line: str) -> str:
    """
    Replace a line in a multiline string by its line number (1-based).

    Args:
        text (str): The original multiline string.
        lineno (int): Line number to replace (1-based).
        new_line (str): The new line content (without newline at end).

    Returns:
        str: Updated multiline string.
    """
    lines = text.splitlines()
    if lineno < 1 or lineno > len(lines):
        raise IndexError(f"Line number {lineno} out of range (1..{len(lines)})")

    lines[lineno - 1] = new_line
    return "\n".join(lines)

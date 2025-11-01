_current_param_row = -1

def set_current_param_row(value: int):
    global _current_param_row
    _current_param_row = value


def get_current_param_row() -> int:
    """Return the current pytest parametrize row index."""
    return _current_param_row

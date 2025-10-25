from pynput import keyboard

_last_key = None
_listener = None

def _on_press(key):
    global _last_key
    try:
        _last_key = key.char if hasattr(key, "char") else key
    except Exception:
        _last_key = key

def get_last_pressed_key():
    """
    Returns the last pressed key if available, or None.
    After returning a key once, resets it to None so that
    the next call won't repeat the old value.
    """
    global _last_key, _listener
    if _listener is None:
        _listener = keyboard.Listener(on_press=_on_press)
        _listener.start()

    key = _last_key
    _last_key = None   # reset after returning
    return key

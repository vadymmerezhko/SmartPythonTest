# utils/keyboard_utils.py

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
    Non-blocking: returns None if no key was pressed yet.
    """
    global _last_key, _listener
    if _listener is None:
        _listener = keyboard.Listener(on_press=_on_press)
        _listener.start()
    return _last_key

from pynput import keyboard

_last_key = None
_listener = None

def _on_press(key):
    global _last_key
    try:
        _last_key = key.char   # normal key like 'a'
    except AttributeError:
        _last_key = key        # special key like ctrl, shift, etc.

def get_last_pressed_key():
    """
    Returns the last pressed key since the listener started, or None if no key yet.
    This is non-blocking.
    """
    global _listener
    if _listener is None:
        # Start background listener once
        _listener = keyboard.Listener(on_press=_on_press)
        _listener.start()
    return _last_key

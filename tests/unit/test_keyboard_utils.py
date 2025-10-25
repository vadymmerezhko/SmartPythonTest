import pytest
from pynput import keyboard
import utils.keyboard_utils as ku


def test_get_last_pressed_key_returns_none_initially(monkeypatch):
    ku._last_key = None
    ku._listener = None

    result = ku.get_last_pressed_key()
    assert result is None


def test_get_last_pressed_key_updates_on_press(monkeypatch):
    ku._last_key = None
    ku._listener = None

    # Simulate pressing Ctrl
    ku._on_press(keyboard.Key.ctrl_l)
    result = ku.get_last_pressed_key()
    assert result == keyboard.Key.ctrl_l


def test_get_last_pressed_key_with_char_key(monkeypatch):
    ku._last_key = None
    ku._listener = None

    # Fake char key
    class FakeKey:
        char = 'a'
    ku._on_press(FakeKey())

    result = ku.get_last_pressed_key()
    assert result == 'a'

import pytest
import sys
from decorators.class_decorators import auto_getters
from pages.dummy_page import DummyPage
from types import SimpleNamespace

# Mock SmartLocator class
class MockSmartLocator:
    def __init__(self, name):
        self.name = name


@pytest.fixture(autouse=True)
def patch_smart_locator(monkeypatch):
    """Patch SmartLocator import in decorator to use MockSmartLocator."""
    monkeypatch.setitem(sys.modules, 'wrappers.smart_locator', SimpleNamespace(SmartLocator=MockSmartLocator))
    yield


@auto_getters
class DummyPage:
    def __init__(self):
        self.title = MockSmartLocator("title")
        self.input_field = MockSmartLocator("input")
        self._private_field = MockSmartLocator("private")  # should be ignored
        self.non_locator = "plain_value"


def test_auto_getters_created():
    page = DummyPage()

    # Check that getter methods exist
    assert hasattr(page, "get_title")
    assert hasattr(page, "get_input_field")

    # Private field and non-locator should not have getters
    assert not hasattr(page, "get__private_field")
    assert not hasattr(page, "get_non_locator")


def test_auto_getters_return_correct_values():
    page = DummyPage()

    # Ensure getter returns the actual locator instance
    assert isinstance(page.get_title(), MockSmartLocator)
    assert page.get_title().name == "title"

    assert isinstance(page.get_input_field(), MockSmartLocator)
    assert page.get_input_field().name == "input"


def test_auto_getters_do_not_override_existing_methods(monkeypatch):
    """Ensure existing get_ methods are not overridden."""
    @auto_getters
    class CustomPage:
        def __init__(self):
            self.title = MockSmartLocator("title")

        def get_title(self):
            return "custom_value"

    page = CustomPage()
    assert page.get_title() == "custom_value"  # original method preserved

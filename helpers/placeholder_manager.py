from utils.code_utils import get_effective_config_value

PLACEHOLDER_PREFIX = "#"
PLACEHOLDER_SUFFIX = "#"

class PlaceholderManager:

    def __init__(self, config: dict):
        self.config = config
        self.placeholders_map = {}

    # Adds a simple key-only or key-value placeholder
    def add_placeholder(self, name: str, value=None):
        self.placeholders_map[name] = str(value) if value is not None else None

    # Removes a simple key-only or key-value placeholder
    def remove_placeholder(self, name: str):
        self.placeholders_map.pop(name, None)

    # Replaces simple key-only or key-value placeholders with their values
    def replace_placeholders_with_values(self, text: str) -> str:
        initial_text = ""

        # Repeat replacements for nested placeholders
        while text != initial_text:
            initial_text = text

            # Replace simple placeholders with their values
            for key, value in self.placeholders_map.items():
                simple_placeholder = get_simple_placeholder_from_name(key)

                if value is None:
                    # Get key-only value from system env variable
                    # or from config parameter
                    # or from command line parameter
                    value = get_effective_config_value(key, self.config)
                    self.placeholders_map[key] = value

                text = text.replace(simple_placeholder, value)
        return text

    # Replaces simple key-only or key-value values with placeholders
    def replace_values_with_placeholders(self, text: str) -> str:

        # Replace simple values with their placeholders
        for key, value in self.placeholders_map.items():
            simple_placeholder = get_simple_placeholder_from_name(key)

            if value is None:
                # Get key-only value from system env variable
                # or from config parameter
                # or from command line parameter
                value = get_effective_config_value(key, self.config)
                self.placeholders_map[key] = value

            text = text.replace(value, simple_placeholder)
        return text

# Create placeholder from its name
def get_simple_placeholder_from_name(name: str) -> str:
    return f"{PLACEHOLDER_PREFIX}{name.upper()}{PLACEHOLDER_SUFFIX}"

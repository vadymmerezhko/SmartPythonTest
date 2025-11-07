def auto_getters(cls):
    """
    Automatically generates getter methods for all SmartLocator attributes
    defined in __init__ after initialization.
    Example: self.title -> get_title()
    """
    original_init = cls.__init__

    def new_init(self, *args, **kwargs):
        # Run the original __init__ first
        original_init(self, *args, **kwargs)

        # Iterate over a static copy to avoid RuntimeError
        for name, value in list(self.__dict__.items()):
            if name.startswith("_"):  # skip private
                continue

            # Generate only for SmartLocator fields
            from wrappers.smart_locator import SmartLocator
            if isinstance(value, SmartLocator):
                getter_name = f"get_{name}"
                if not hasattr(self, getter_name):
                    # Bind name properly in lambda default arg
                    setattr(self, getter_name, lambda n=name: getattr(self, n))

    cls.__init__ = new_init
    return cls

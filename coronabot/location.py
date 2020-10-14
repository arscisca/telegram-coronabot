class Location:
    def __init__(self, name, level):
        self.name = name
        self.level = level

    @staticmethod
    def resolve_alias(lname, aliases):
        """Map an aliased location name to its standard form.
        Args:
            lname (str): location name
            aliases (dict): a dictionary mapping each possible alias to the standard location name
        Return:
            str: standard location name. If location does not appear in `aliases` dict, it is returned unchanged.
        """
        if lname in aliases:
            return aliases[lname]
        return lname

    def __str__(self):
        """Convert to string"""
        return self.name.title()

    class LocationError(ValueError):
        """Exception for invalid locations"""
        pass

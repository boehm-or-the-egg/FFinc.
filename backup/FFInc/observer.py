class Observer:
    """Base class for an observer in the observer pattern."""
    def update(self, message: str):
        """Called by the subject to update the observer."""
        raise NotImplementedError("Subclass must implement update method")

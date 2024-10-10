class Subject:
    """Base class for any subject in the observer pattern."""
    def __init__(self):
        self._observers = []

    def add_observer(self, observer):
        """Attach an observer to the subject."""
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer):
        """Detach an observer from the subject."""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify_observers(self, message: str):
        """Notify all attached observers."""
        for observer in self._observers:
            observer.update(message)


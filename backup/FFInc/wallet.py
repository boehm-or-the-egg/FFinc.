from backup.FFInc.observer import Observer
from PyQt6.QtCore import QObject


CREDITS_PER_SECOND = 3
CREDITS_SAVE_FILE = "../app_data.json"
CHECK_INTERVAL_RUNNING = 5
UNVAULT_FEE = 120000
SIZE_THRESHOLD = 2048 * 1024
TIMESTEP = 1

class Wallet(QObject,Observer):
    def __init__(self, file_manager):
        self.file_manager = file_manager
        self.total_credits = 0
        self.load_credits()

    def save_credits(self):
        """Save the credits data using FileManager."""
        data = self.file_manager.load_data()
        data['credits']['total_credits'] = round(self.total_credits)

        self.file_manager.save_data(data)

    def load_credits(self):
        """Load the credits data using FileManager."""
        data = self.file_manager.load_data()
        self.total_credits = data['credits'].get('total_credits', 0)

    def update_credits(self, delta):
        """Updates the real-time credits and saves the changes."""
        self.total_credits += delta
        self.save_credits()

    def add_credits(self, amount):
        """Adds FlowCreds to the user's balance."""
        if amount < 0:
            return
        self.total_credits += amount
        self.save_credits()

    def deduct_credits(self, amount):
        """Deducts FlowCreds from the user's balance if sufficient credits are available."""
        if amount < 0:
            return
        if amount > self.total_credits:
            raise ValueError("Insufficient credits to deduct.")
        self.total_credits -= amount
        self.save_credits()

    def get_total_credits(self):
        """Returns the total credits ever earned by the user."""
        return self.total_credits

    @property
    def __str__(self):
        """String representation for easy viewing of the FlowCred system status."""
        return f"Total FlowCreds Earned: {self.total_credits}"
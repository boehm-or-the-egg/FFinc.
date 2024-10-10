from backup.FFInc.subject import Subject
import threading
import time
import psutil
from PyQt6.QtCore import QTimer,pyqtSlot, pyqtSignal, QObject

CREDITS_PER_SECOND = 3
CREDITS_SAVE_FILE = "../app_data.json"
CHECK_INTERVAL_RUNNING = 5
UNVAULT_FEE = 120000
SIZE_THRESHOLD = 2048 * 1024
TIMESTEP = 1

class AppManager(QObject, Subject):
    DATA_FILE = '../app_data.json'
    app_rented_signal = pyqtSignal(str)
    app_vaulted_signal = pyqtSignal(str)
    app_unvaulted_signal = pyqtSignal(str)
    rental_expired_signal = pyqtSignal(str)

    def __init__(self, file_manager, wallet):
        super().__init__()
        self.rental_check_timer = None
        self.monitoring_timer = None
        self.file_manager = file_manager
        self.wallet = wallet
        self.vaulted_apps = {}
        self.lock = threading.Lock()
        self.load_data()
        self.start_rental_check()
        self.start_monitoring()

    def start_monitoring(self):
        """Start a timer to regularly check and kill vaulted apps."""
        self.monitoring_timer = QTimer(self)
        self.monitoring_timer.timeout.connect(self.check_and_kill_vaulted_apps)
        self.monitoring_timer.start(CHECK_INTERVAL_RUNNING * 1000)

    def save_data(self):
        """Save the vaulted apps data using FileManager."""
        data = self.file_manager.load_data()
        data['apps']['vaulted_apps'] = self.vaulted_apps
        self.file_manager.save_data(data)

    def load_data(self):
        """Load the vaulted apps data using FileManager."""
        data = self.file_manager.load_data()
        self.vaulted_apps = data['apps'].get('vaulted_apps', {})

    def vault_app(self, app_name):
        if app_name in self.vaulted_apps:
            return

        self.vaulted_apps[app_name] = {
            'is_vaulted': True,
            'is_rented': False,
            'vault_time': time.time(),
            'start_time': None,
            'end_time': None
        }
        self.save_data()

    def unvault_app(self, app_name):
        with self.lock:
            if app_name in self.vaulted_apps:
                del self.vaulted_apps[app_name]
                self.save_data()
            else:
                return

    def rent_app(self, app_name, duration_minutes):
        """Rent the specified app for a given duration."""
        with self.lock:

            if app_name in self.vaulted_apps and self.vaulted_apps[app_name]['is_rented']:
                self.app_rented_signal.emit(f"{app_name} is already rented.")
                return

            if app_name not in self.vaulted_apps:
                self.app_rented_signal.emit(f"{app_name} is not vaulted and cannot be rented.")
                return

            self.vaulted_apps[app_name]['is_rented'] = True

            start_time = time.time()
            end_time = start_time + (duration_minutes * 60)

            self.vaulted_apps[app_name]['start_time'] = start_time
            self.vaulted_apps[app_name]['end_time'] = end_time

            self.flow_cred_system.deduct_credits(rental_cost)

            self.app_rented_signal.emit(f"Rented {app_name} for {duration_minutes} minutes.")

            self.save_data()

    def check_and_kill_vaulted_apps(self):
        self.load_data()
        """Check for running vaulted apps and kill them if necessary."""
        with self.lock:
            for app_name, app_data in self.vaulted_apps.items():
                if app_data['is_vaulted'] and not app_data['is_rented']:
                    self.kill_app_if_running(app_name)

    def kill_app_if_running(self, app_name):
        """Kill all instances of the specified application if they are running and not rented."""
        processes_killed = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if app_name.lower() in proc.info['name'].lower():
                    proc.terminate()
                    proc.wait(timeout=5)
                    processes_killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                return

        if processes_killed > 0:

            self.on_app_killed(app_name)
        else:
            return

    @pyqtSlot(str)
    def on_app_killed(self, app_name):
        return

    def start_rental_check(self):
        """Start a timer to check for rental expirations."""
        self.rental_check_timer = QTimer(self)
        self.rental_check_timer.timeout.connect(self.check_rental_expirations)
        self.rental_check_timer.start(CHECK_INTERVAL_RUNNING * 1000)

    def check_rental_expirations(self):
        """Check for expired rentals and handle them."""
        current_time = time.time()
        expired_apps = []

        with self.lock:
            for app_name, app_data in self.vaulted_apps.items():
                if app_data['is_rented'] and app_data['end_time'] <= current_time:
                    app_data['is_rented'] = False
                    app_data['start_time'] = None
                    app_data['end_time'] = None
                    expired_apps.append(app_name)
        self.save_data()
        for app_name in expired_apps:
            self.on_rental_expired(app_name)

    @pyqtSlot(str)
    def on_rental_expired(self, app_name):
        """Handle what happens when the rental expires."""
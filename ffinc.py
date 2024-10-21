import os, sys, json, shutil, threading, time, psutil, win32com.client
from typing import Any, Dict
from pygame import mixer
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal, QObject, QTimer, QThread, QSize, QCoreApplication
from PyQt6.QtGui import QIcon, QFont, QFontDatabase, QAction, QColor, QPixmap, QGuiApplication, QPainterPath
from PyQt6.QtWidgets import (QMainWindow, QListWidget, QVBoxLayout, QWidget, QLineEdit, QListWidgetItem, QPushButton,
                             QMessageBox, QDialog, QSpinBox, QLabel, QHBoxLayout, QFileDialog, QApplication,
                             QSystemTrayIcon, QMenu, QSizePolicy, QCheckBox, QFrame, QGraphicsBlurEffect,
                             QGraphicsDropShadowEffect, QProgressBar )

# Constants
CREDITS_PER_SECOND = 1
CHECK_INTERVAL_RUNNING = 5
UNVAULT_FEE = 120000
SIZE_THRESHOLD = 2048 * 1024  # 2 MB

style_sheet = """
                QWidget {
                    background-color: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 1,
                        stop: 0 #2E3440,
                        stop: 1 #3B4252
                    );
                    border-radius: 15px;
                    color: #ECEFF4;
                    font-family: "Feature Mono";
                    font-size: 12pt;
                }
               
                
                QFrame {
                    background: transparent;
                    border: none;

                }

                QPushButton {
                    background-color: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 1,
                        stop: 0 #4C566A,
                        stop: 1 #434C5E
                    );
                    border: 2px solid #4C566A;
                    border-radius: 10px;
                    color: #ECEFF4;
                    padding: 5px;
                    font-size: 11pt;
                    font-weight: bold;
                    text-align: center;
                    margin:2px;
                }
                QPushButton#confirm_button {
                    background-color: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 1,
                        stop: 0 #4C566A,
                        stop: 1 #434C5E
                    );
                    border: 2px solid #4C566A;
                    border-radius: 10px;
                    color: #ECEFF4;
                    padding: 5px;
                    font-size: 11pt;
                    font-weight: bold;
                    text-align: center;
                    margin:5px;
                }

                QPushButton#bubble {
                    background-color: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 1,
                        stop: 0 #4C566A,
                        stop: 1 #434C5E
                    );
                    border: 2px solid #4C566A;
                    border-radius: 24px;
                    color: #ECEFF4;
                    padding: 5px;
                    margin:5px;
                    height: 35px;
                    width: 35px;
                }
                QPushButton#bubble:hover {
                    background-color: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 1,
                        stop: 0 #5E81AC,
                        stop: 1 #4C566A
                    );
                }

                QPushButton:hover {
                    background-color: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 1,
                        stop: 0 #5E81AC,
                        stop: 1 #4C566A
                    );
                }

                QPushButton:pressed {
                    background-color: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 1,
                        stop: 0 #81A1C1,
                        stop: 1 #5E81AC
                    );
                }
                QPushButton#bubble:pressed {
                    background-color: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 1,
                        stop: 0 #81A1C1,
                        stop: 1 #5E81AC
                    );
                }

                QPushButton:disabled {
                    background-color: #4C566A;
                    color: #81A1C1;
                }
                QCheckBox {
                    background-color: transparent;
                    check-color: #ECEFF4;
                    radius: 5px;

                }
                QCheckBox:disabled {
                    color: #4C566A;
                    check-color: #4C566A;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border: 2px solid #4C566A;
                    check-color: #ECEFF4;
                }
                QCheckBox::indicator:checked {
                    background-color: #5E81AC;
                }

                QCheckBox::indicator:hover {
                    width: 20px;
                    height: 20px;
                    border: 2px solid #4C566A;

                }

                QLineEdit, QTextEdit {
                    background-color: rgba(255, 255, 255, 0.1);
                    border: 1px solid #4C566A;
                    border-radius: 8px;
                    color: #ECEFF4;
                    padding: 5px;
                    font-size: 10pt;
                }

                QLineEdit:hover, QTextEdit:hover {
                    background-color: rgba(255, 255, 255, 0.15);
                }

                QLineEdit:focus, QTextEdit:focus {
                    border: 2px solid #5E81AC;
                }

                QFrame#line_separator_app {
                    background-color: #4C566A;
                }

                QFrame#line_separator_vault {
                    background-color: #4C566A;
                    padding: 10px;
                }

                QMenu {
                    background-color: #2E3440;
                    color: #ECEFF4;
                    border: 1px solid #4C566A;
                }

                QMenu::item {
                    padding: 5px 20px;
                }

                QMenu::item:selected {
                    background-color: #4C566A;
                }

                QSystemTrayIcon {
                    icon-size: 24px;
                }

                /* Shadows and Transparency */
                QFrame, QPushButton {
                    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2);
                }

                /* Scrollbars */
                QScrollBar {
                    border: 2px solid #4C566A;
                    background-color: transparent;
                    border-radius: 5px;
                    width: 10px;
                    position: absolute;
                }

               QScrollBar::handle:vertical {
                    background-color: #5E81AC;
                    border-radius: 3px;
                }

                /* Adjust handle appearance when hovered or pressed */
                QScrollBar::handle:vertical:hover {
                    background-color: #4C6B88; /* Change color on hover */
                }

                QScrollBar::handle:vertical:pressed {
                    background-color: #3B5B7A; /* Change color when pressed */
                }

                QScrollBar::add-line:vertical,
                QScrollBar::sub-line:vertical {
                    height: 0; /* Hide arrows */
                }

                /* Hide selection indicator by removing background or outline */
                QScrollBar::handle:vertical:selected {
                    background-color: #5E81AC; /* Keep the handle color consistent */
                }

                /* Tooltips */
                QToolTip {
                    background-color: #4C566A;
                    color: #ECEFF4;
                    border: 1px solid #81A1C1;
                    padding: 5px;
                    border-radius: 5px;
                }
                QSpinBox {
                    background-color: transparent;
                    border: 2px solid #4C566A;
                    border-radius: 8px;
                    color: #ECEFF4;
                    padding: 5px;
                    font-size: 11pt;
                }

                QSpinBox::up-button {
                    background-color: #4C566A;
                    border: none;
                    subcontrol-origin: border;
                    subcontrol-position: top right;
                    width: 10px;
                    height: 10px;
                    border-radius: 5px; /* Circular button */
                    margin-right: 6px; /* Moves the button away from the right edge */
                    margin-top: 6px; /* Moves the button down slightly from the top edge */
                }

                QSpinBox::down-button {
                    background-color: #4C566A;
                    border: none;
                    subcontrol-origin: border;
                    subcontrol-position: bottom right;
                    width: 10px;
                    height: 10px;
                    border-radius: 5px; /* Circular button */
                    margin-right: 6px; /* Moves the button away from the right edge */
                    margin-bottom: 6px; /* Moves the button down slightly from the top edge */
                }

                QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                    background-color: #ECEFF4; /* Slightly off-white on hover */
                }

                QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
                    background-color: #D8DEE9; /* Even lighter shade on press */
                }
                QListWidget {
                    background-color: transparent;
                    border: 2px solid #4C566A;
                    color: #ECEFF4;
                    margin: 5px;
                    padding-right: 5px;
                    padding-left: 6px;
                    padding-bottom: 5px;
                    padding-top: 5px;
                }
                QListWidget::item {
                    margin: 3px;
                }
                QListWidget::item:selected {
                    background-color: #5E81AC;
                    border-radius: 10px;
                    selection-color: #ECEFF4;
                    elevation: 5;    
                }
                QListWidget::item:selected:!active {
                    background-color: #5E81AC;
                    border-radius: 10px;
                    selection-color: #ECEFF4;
                    elevation: 5;
                }
                QListWidget::item:hover {
                    background-color: #4C566A;
                    border-radius: 10px;
                }
                QProgressBar {
                    border: 2px solid #4C566A;
                    border-radius: 10px;
                    background-color: #4C566A;
                    progress-color: #5E81AC;
                    color: #ECEFF4;
                    text-align: center;
                    height: 10px;
                }
                """

class FileManager:
    _instance = None
    _lock = threading.Lock()
    DEFAULT_DATA_FILE = 'app_data.json'
    DEFAULT_STRUCTURE = {
        'apps': {
            'vaulted_apps': {},
        },
        'credits': {
            'total_credits': 0
        },
        'settings': {
            'first_launch': True,
            'start_on_startup': False
        }
    }

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one instance is created."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_file: str = DEFAULT_DATA_FILE):
        if self._initialized:
            return

        self.data_file = data_file
        self.temp_file = f"{data_file}.tmp"
        self.lock = threading.Lock()

        self._initialized = True

    @staticmethod
    def _validate_json_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures the required keys are present and initializes any missing ones."""

        def recursive_update(d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
            for k, v in u.items():
                if isinstance(v, dict):
                    d[k] = recursive_update(d.get(k, {}), v)
                else:
                    d.setdefault(k, v)
            return d

        return recursive_update(data, FileManager.DEFAULT_STRUCTURE)

    def load_data(self) -> Dict[str, Any]:
        """Thread-safe load method."""
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        return self._validate_json_data(data)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error loading data: {e}")
                    return self._validate_json_data({})
            else:
                return self._validate_json_data({})

    def save_data(self, data: Dict[str, Any]) -> None:
        """Thread-safe, atomic save method."""
        with self.lock:
            data = self._validate_json_data(data)

            try:
                with open(self.temp_file, 'w', encoding='utf-8') as temp_file:
                    json.dump(data, temp_file, indent=4)
                shutil.move(self.temp_file, self.data_file)
            except IOError as e:
                print(f"Error saving data: {e}")

    def is_first_launch(self) -> bool:
        """Check if it's the first launch."""
        data = self.load_data()
        return data.get('settings', {}).get('first_launch', True)

    def is_launch_on_startup(self) -> bool:
        """Check if it's the first launch."""
        data = self.load_data()
        return data.get('settings', {}).get('start_on_startup', True)

    def set_first_launch_done(self) -> None:
        """Update the state to indicate that the first launch has occurred."""
        data = self.load_data()
        data['settings']['first_launch'] = False
        self.save_data(data)


class SystemAppScanner:
    def __init__(self):
        self.lock = threading.Lock()
        self.cache = None

    def scan_running_apps(self, force_refresh=False):
        """Scans all running apps (non-system) and returns a list of app info. Uses cached results if available unless forced to refresh."""
        with self.lock:
            if self.cache is not None and not force_refresh:
                return self.cache
            self.cache = self.get_non_system_apps()
            return self.cache

    @staticmethod
    def get_non_system_apps():
        """Get non-system apps and filter out system-related executables and drivers."""
        system_apps = {'svchost.exe', 'explorer.exe', 'system', 'registry', 'idle', 'nissrv.exe',
                       'mpdefendercoreservice.exe', 'msmpeng.exe'}
        system_dirs = ['C:\\Windows', 'C:\\Windows\\System32']
        running_apps = []
        exe_paths = set()

        for proc in psutil.process_iter(['name', 'exe']):
            try:
                name = proc.info['name']
                exe_path = proc.info['exe']
                if exe_path and name:
                    exe_path_lower = exe_path.lower()
                    if (name.lower() not in system_apps and
                            not any(exe_path_lower.startswith(system_dir.lower()) for system_dir in system_dirs) and
                            exe_path not in exe_paths):
                        app_size = os.path.getsize(exe_path)
                        if app_size > SIZE_THRESHOLD:
                            running_apps.append({'name': name, 'exe': exe_path, 'size': app_size})
                            exe_paths.add(exe_path)
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                continue

        return sorted(running_apps, key=lambda x: x['size'], reverse=True)


class AudioCue:
    def __init__(self, audio_file):
        self.toast = None
        mixer.init()
        self.audio_file = audio_file
        self.play_audio_in_thread()  # Play sound asynchronously

    def play_audio(self):
        try:
            # Load and play the sound
            sound = mixer.Sound(self.audio_file)
            sound.play()
        except Exception as e:
            self.toast = ToastNotifier(f"Error playing sound: {e}")

    def play_audio_in_thread(self):
        # Create a new thread to play sound asynchronously
        threading.Thread(target=self.play_audio, daemon=True).start()


class Wallet:
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
        return f"Total Earned: {self.total_credits}"


class AppManager(QObject):
    DATA_FILE = '../app_data.json'
    app_rented_signal = pyqtSignal(str)
    app_vaulted_signal = pyqtSignal(str)
    app_unvaulted_signal = pyqtSignal(str)
    rental_expired_signal = pyqtSignal(str)

    def __init__(self, file_manager, flow_cred_system: 'Wallet'):
        super().__init__()
        self.rental_check_timer = None
        self.monitoring_timer = None
        self.file_manager = file_manager
        self.flow_cred_system = flow_cred_system
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
        self.on_app_vaulted(app_name)

    def unvault_app(self, app_name):
        with self.lock:
            if app_name in self.vaulted_apps:
                del self.vaulted_apps[app_name]
                self.save_data()
                self.on_on_app_unvaulted(app_name)
            else:
                return

    def rent_app(self, app_name, duration_minutes):
        """Rent the specified app for a given duration."""
        with self.lock:

            if app_name in self.vaulted_apps and self.vaulted_apps[app_name]['is_rented']:
                self.app_rented_signal.emit(f"{app_name.removesuffix(".exe")} is already rented.")
                return

            rental_cost = duration_minutes * 120
            if self.flow_cred_system.get_total_credits() < rental_cost:
                self.app_rented_signal.emit("You do not have enough credits to rent this app.")
                return

            if app_name not in self.vaulted_apps:
                self.app_rented_signal.emit(f"{app_name.removesuffix(".exe")} is not vaulted and cannot be rented.")
                return

            self.vaulted_apps[app_name]['is_rented'] = True

            start_time = time.time()
            end_time = start_time + (duration_minutes * 60)

            self.vaulted_apps[app_name]['start_time'] = start_time
            self.vaulted_apps[app_name]['end_time'] = end_time

            self.flow_cred_system.deduct_credits(rental_cost)

            self.app_rented_signal.emit(f"Rented {app_name.removesuffix(".exe")} for {duration_minutes} minutes.")

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

    def _show_message(self, message, is_mute):
        if not is_mute:
            AudioCue("resources/audio/notification.wav")
        self.toast = ToastNotifier(message)
        self.toast.display


    def _show_warning(self, message):
        AudioCue("resources/audio/warning.wav")
        self.toast = ToastNotifier(message)
        self.toast.display


    @pyqtSlot(str)
    def on_app_killed(self, app_name):
        self._show_message(f"Killed {app_name.removesuffix(".exe")}!", False)
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
        self._show_warning(f"Rental for {app_name.removesuffix(".exe")} has expired.")

    def on_app_vaulted(self, app_name):
        self._show_message(f"Vaulted {app_name.removesuffix(".exe")}!", False)

    def on_on_app_unvaulted(self, app_name):
        self._show_message(f"Unvaulted {app_name.removesuffix(".exe")}!", False)


class LaunchOnStartQuery(QDialog):

    def __init__(self, file_manager):

        super().__init__()
        self.setStyleSheet(style_sheet)
        self.file_manager = file_manager
        self.setWindowTitle("First Launch")
        self.setWindowIcon(QIcon("resources/icons/FFInc-Icon.ico"))
        self.layout = QVBoxLayout()
        self.label = QLabel("Would you like to start the System App Scanner on startup?")
        self.startup_checkbox = QCheckBox("Start on system startup")
        self.start_button = QPushButton("Confirm")
        self.start_button.clicked.connect(self.startup_launch)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.startup_checkbox)
        self.layout.addWidget(self.start_button)
        self.setLayout(self.layout)

    def startup_launch(self):
        """Set the startup launch preference and close the dialog."""
        data = self.file_manager.load_data()
        data['settings']['start_on_startup'] = self.startup_checkbox.isChecked()
        self.file_manager.save_data(data)
        self.close()

    def add_to_startup(self):
        print("Adding to startup")
        if self.file_manager.is_launch_on_startup():
            startup_folder = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs",
                                          "Startup")
            app_name = "FFInc.exe"
            app_path = os.path.join(os.path.dirname(sys.executable), app_name)

            shortcut_path = os.path.join(startup_folder, app_name + ".lnk")
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = app_path
            shortcut.WorkingDirectory = os.path.dirname(app_path)
            shortcut.save()
            print("Added to startup")
        print("Not added to startup")
        

class RentDialog(QDialog):
    def __init__(self, credits_per_minute, wallet, parent=None):
        super().__init__(parent)
        self.credits_per_minute = credits_per_minute
        self.current_price = 0
        self.wallet = wallet
        self.available_credits = self.wallet.get_total_credits()
        self.setStyleSheet(style_sheet)
        layout = QHBoxLayout()

        self.instruction_label = QLabel("Select the duration in minutes:")
        layout.addWidget(self.instruction_label)

        self.time_spinner = QSpinBox()
        self.time_spinner.setSuffix(" m")
        self.time_spinner.setRange(5, 120)
        self.time_spinner.setValue(5)
        layout.addWidget(self.time_spinner)

        payout = QVBoxLayout()
        payout.addLayout(layout)
        line_separator = QFrame()
        line_separator.setFrameShape(QFrame.Shape.HLine)
        line_separator.setFrameShadow(QFrame.Shadow.Sunken)
        line_separator.setLineWidth(5)
        line_separator.setObjectName("line_separator_vault")
        payout.addWidget(line_separator)

        self.price_label = QLabel(f"Price: {self.current_price}")
        payout.addWidget(self.price_label)

        self.balance_label = QLabel(f"Balance: {self.available_credits}")
        payout.addWidget(self.balance_label)

        self.time_spinner.valueChanged.connect(self.update_price_and_balance)

        self.confirm_button = QPushButton("Rent")
        self.confirm_button.setObjectName("confirm_button")
        self.confirm_button.clicked.connect(self.accept)
        payout.addWidget(self.confirm_button)

        self.setLayout(payout)

        self.update_price_and_balance()

    def update_price_and_balance(self):
        """Update the price label and check if the user has enough credits."""
        time_in_minutes = self.time_spinner.value()
        self.current_price = time_in_minutes * self.credits_per_minute
        self.price_label.setText(f"Price: {self.current_price}")

        self.available_credits = self.wallet.get_total_credits()
        self.balance_label.setText(f"Available Credits: {self.available_credits}")

        if self.current_price > self.available_credits:
            self.price_label.setStyleSheet("color: red;")
            self.confirm_button.setEnabled(False)
        else:
            self.price_label.setStyleSheet("color: green;")
            self.confirm_button.setEnabled(True)

    def get_duration_and_price(self):
        """Return the selected duration and price."""
        return self.time_spinner.value(), self.current_price


class AppListWidget(QWidget):
    # noinspection PyUnresolvedReferences
    def __init__(self, scanner, app_manager, vault_window, file_manager):
        super().__init__()
        self.flow_cred_system = Wallet(file_manager)
        self.scanner = scanner
        self.app_manager = app_manager
        self.vault_window = vault_window
        self.setWindowTitle("Running Applications")

        self.layout = QVBoxLayout(self)
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search for applications...")
        self.layout.addWidget(self.search_bar)

        self.app_list = QListWidget(self)
        self.layout.addWidget(self.app_list)
        self.app_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.add_to_vault_button = QPushButton("Confirm", self)
        # noinspection PyUnresolvedReferences
        self.add_to_vault_button.clicked.connect(self.add_to_vault)
        self.layout.addWidget(self.add_to_vault_button)

        self.refresh_button = QPushButton("Refresh", self)
        self.refresh_button.clicked.connect(self.manual_refresh_scan)
        self.layout.addWidget(self.refresh_button)

        self.setLayout(self.layout)

        self.running_apps = []
        self.filtered_apps = []

        self.search_bar.textChanged.connect(self.filter_apps)

        self.app_manager.app_rented_signal.connect(self.on_app_rented)

        self.is_scanning = False

    def manual_refresh_scan(self):
        """Manually triggers a scan when the 'Refresh' button is pressed."""
        if not self.is_scanning:
            self.update_app_list(force_refresh=True)

    def update_app_list(self, force_refresh=False):
        """Update the list of running applications."""
        if self.is_scanning:
            return
        self.is_scanning = True
        threading.Thread(target=self._scan_apps, daemon=True, args=(force_refresh,)).start()

    def _scan_apps(self, force_refresh):

        """Thread target to scan apps and progressively update the UI."""
        try:
            running_apps = self.scanner.scan_running_apps(force_refresh=force_refresh)


            self.running_apps = running_apps
            self.filtered_apps = self.filter_applications(self.running_apps)
            QTimer.singleShot(0, self.update_app_list_ui)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to scan applications: {str(e)}")
        finally:
            self.is_scanning = False

    def update_app_list_ui(self):
        """Update the UI with the new app list."""
        self.app_list.clear()
        for application in self.filtered_apps:
            item = QListWidgetItem(application['name'])
            item.setData(Qt.ItemDataRole.UserRole, application['exe'])
            self.app_list.addItem(item)

    @staticmethod
    def filter_applications(apps):
        """Filter out duplicates, system apps, and small executables, and sort by size."""
        unique_apps = {}
        system_apps = {'svchost.exe', 'explorer.exe', 'system', 'registry', 'idle'}

        for application in apps:
            name_lower = application['name'].lower()
            if name_lower not in system_apps and application['exe'] not in unique_apps:
                exe_path = application['exe']
                if os.path.exists(exe_path) and os.path.getsize(exe_path) > SIZE_THRESHOLD:
                    unique_apps[application['exe']] = application

        return sorted(unique_apps.values(), key=lambda x: os.path.getsize(x['exe']), reverse=True)

    def filter_apps(self):
        """Filter the application list based on the search input."""
        search_text = self.search_bar.text().lower()
        self.app_list.clear()

        for application in self.filtered_apps:
            if search_text in application['name'].lower():
                item = QListWidgetItem(application['name'])
                item.setData(Qt.ItemDataRole.UserRole, application['exe'])
                self.app_list.addItem(item)

    def add_to_vault(self):
        """Add selected application to the vault."""
        try:
            selected_items = self.app_list.selectedItems()
            if not selected_items:
                self._show_warning("No application selected to add to vault.")
                return

            for item in selected_items:
                exe_path = item.data(Qt.ItemDataRole.UserRole)
                app_name = os.path.basename(exe_path)

                if not exe_path or not os.path.exists(exe_path):
                    self._show_warning(f"The application '{app_name}' does not exist.")
                    continue

                try:
                    name = str(app_name).removesuffix('.exe')
                    reply = QMessageBox.question(
                        self,
                        f"Are you sure you want to vault {name}?",
                        f"{name} will be permanently blocked unless unvaulted or rented.",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        self.app_manager.vault_app(app_name)
                        self.vault_window.refresh_vaulted_apps()
                    else:
                        return
                except Exception as e:
                    self._show_warning(f"Failed to add {app_name} to the vault: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while adding to vault: {str(e)}")

    @pyqtSlot(str)
    def on_app_rented(self, message):
        """Handle rental status messages."""
        self._show_message(message, False)

    def _show_message(self, message, is_mute):
        if not is_mute:
            AudioCue("resources/audio/notification.wav")
        self.toast = ToastNotifier(message)
        self.toast.display


    def _show_warning(self, message):
        AudioCue("resources/audio/warning.wav")
        self.toast = ToastNotifier(message)
        self.toast.display


class TimerApp(QWidget):
    configuration_confirmed = pyqtSignal()

    def __init__(self, flow_cred_system, app_manager):
        super().__init__()

        self.global_remaining_time = None
        self.file_manager = FileManager()
        self.flow_cred_system = flow_cred_system
        self.remaining_time = 0
        self.app_manager = app_manager
        self.is_running = False
        self.is_paused = False
        self.session_completed = False
        self.bonus_multiplier = 1.0
        self.bonus_credits = 0
        self.auto_pause_duration = 0
        self.break_time = 0
        self.in_break = False
        self.completed_intervals = 0

        self.credits_label = QLabel()
        self.layout = QVBoxLayout()
        self.timer_label = QLabel("00:00:00")
        self.bonus_label = QLabel("(+0%) Bonus: 0")
        self.claim_bonus_button = QPushButton("Claim Bonus")
        self.start_button = QPushButton("Start")
        self.pause_resume_button = QPushButton("Pause")
        self.configure_button = QPushButton("Configure Session")
        self.pomodoro_duration = QSpinBox()
        self.pomodoro_count = QSpinBox()
        self.timer = QTimer()
        self.skip_break = QCheckBox("Skip Breaks")
        self.init_ui()
        self.app_manager.app_rented_signal.connect(self.update_after_rent)

    def init_ui(self):
        self.layout = QVBoxLayout()

        # Credits label
        self.credits_label = QLabel(f"Wealth: {self.flow_cred_system.get_total_credits()}")
        self.layout.addWidget(self.credits_label)
        self.credits_label.setStyleSheet("font-size: 24px;")

        # Timer label centered
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setStyleSheet("font-size: 82px; font-weight:bold ;font-family: 'Feature Mono';")
        self.timer_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        timer_layout = QHBoxLayout()
        timer_layout.addStretch()
        timer_layout.addWidget(self.timer_label)
        timer_layout.addStretch()
        timer_layout.setContentsMargins(0, 20, 0, 0)
        self.layout.addLayout(timer_layout)

        # Bonus label
        self.bonus_label = QLabel("(+0%) Bonus: 0")
        self.bonus_label.setStyleSheet("font-size: 18px;")
        self.bonus_label.hide()
        self.layout.addWidget(self.bonus_label)

        # Claim bonus button
        self.claim_bonus_button = QPushButton("Claim Bonus")
        self.claim_bonus_button.setEnabled(False)
        self.claim_bonus_button.hide()
        self.claim_bonus_button.clicked.connect(self.claim_bonus)
        self.layout.addWidget(self.claim_bonus_button)

        # Pomodoro duration and count setup
        self.pomodoro_duration.lineEdit().setReadOnly(True)
        self.pomodoro_count.lineEdit().setReadOnly(True)
        self.pomodoro_duration.setRange(15, 120)
        self.pomodoro_duration.setSingleStep(CHECK_INTERVAL_RUNNING)
        self.pomodoro_duration.setPrefix("Pomodoro duration: ")
        self.pomodoro_count.setRange(1, 12)
        self.pomodoro_count.setPrefix("Count:")
        self.pomodoro_count.setValue(2)
        self.pomodoro_duration.setMinimumWidth(250)
        self.pomodoro_count.setMinimumWidth(150)

        # Time input layout
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.pomodoro_duration)
        time_layout.addWidget(self.pomodoro_count)
        self.layout.addLayout(time_layout)

        self.hide_time_inputs()

        # Configure button
        self.configure_button = QPushButton("Configure Session")
        self.configure_button.clicked.connect(self.show_time_inputs)
        self.layout.addWidget(self.configure_button)

        # Button layout for start, pause/resume, and skip break
        button_layout = QHBoxLayout()
        self.start_button.clicked.connect(self.start_cancel_session)
        button_layout.addWidget(self.start_button)
        self.pause_resume_button = QPushButton("Pause")
        self.pause_resume_button.clicked.connect(self.pause_resume_session)
        self.pause_resume_button.setEnabled(False)
        button_layout.addWidget(self.pause_resume_button)
        self.skip_break = QCheckBox("Skip Breaks")
        button_layout.addWidget(self.skip_break)

        self.layout.addLayout(button_layout)

        # Set the main layout
        self.setLayout(self.layout)

        # Connect timer signal
        self.timer.timeout.connect(self.update_timer)

    def start_session(self):
        pomodoro_duration = self.pomodoro_duration.value() * 60
        pomodoro_count = self.pomodoro_count.value()
        total_duration = pomodoro_duration * pomodoro_count

        self._initialize_session_state(pomodoro_duration, total_duration)

        if total_duration > 3600:  # 1 hour
            self._calculate_bonus(total_duration, pomodoro_count)
        else:
            self._reset_bonus()
        self._setup_ui_for_session()
        self.timer.start(1000)
        AudioCue("resources/audio/timer_start.wav")

    def interrupt_session(self):
        if self._confirm_dialog("Interrupt", "Are you sure you want to interrupt the session?"):
            self.end_session(interrupted=True)

    def end_session(self, interrupted=False):
        self.timer.stop()
        self._reset_ui_after_session()

        if interrupted:
            self._handle_interruption()
        else:
            self._handle_completion()

    def trigger_auto_break(self):
        """Trigger a break if the skip break checkbox is not checked, otherwise skip directly to the next subsession."""
        if not self.skip_break.isChecked():
            AudioCue("resources/audio/break.wav")
            self.in_break = True
            self.break_time = int(self.pomodoro_duration.value() * 60 * 0.2)
            self.update_timer_label()
            self.timer.start(1000)
            self._show_message("Good Work! I started a break for you.", True)
        else:
            self.start_next_subsession()

    def end_break(self):
        self._show_message("Break over! Starting the next session.", False)
        self.in_break = False
        self.start_next_subsession()

    def start_next_subsession(self):
        """Start the next subsession if available, otherwise end the session."""
        if self.completed_intervals < self.pomodoro_count.value():
            self.remaining_time = self.pomodoro_duration.value() * 60
            self.update_timer_label()
            self.timer.start(1000)

        else:
            self.end_session()

    def _initialize_session_state(self, session_duration, total_duration):
        self.remaining_time = session_duration
        self.global_remaining_time = total_duration
        self.session_completed = False
        self.auto_pause_duration = session_duration * 0.2

    def _calculate_bonus(self, total_duration, pomodoro_count):
        self.bonus_multiplier = self.calculate_bonus(total_duration / 3600)
        self.bonus_credits = (total_duration + (self.auto_pause_duration * (pomodoro_count - 1))) * (
                self.bonus_multiplier - 1
        )
        self.update_bonus_label()
        self.bonus_label.show()

    def _reset_bonus(self):
        self.bonus_multiplier = 1.0
        self.bonus_credits = 0

    def _setup_ui_for_session(self):
        self.claim_bonus_button.setEnabled(False)
        self.configure_button.setEnabled(False)
        self.claim_bonus_button.hide()
        self.bonus_label.hide()
        self.skip_break.setEnabled(False)
        self.update_timer_label()
        self.is_running = True
        self.is_paused = False
        self.pause_resume_button.setEnabled(True)

    def _reset_ui_after_session(self):
        self.is_running = False
        self.start_button.setText("Start")
        self.pause_resume_button.setEnabled(False)
        self.configure_button.setEnabled(True)
        self.skip_break.setEnabled(True)

    def _handle_interruption(self):
        self.bonus_label.hide()
        self.claim_bonus_button.hide()
        self._show_warning("Your session was interrupted. No bonus will be applied.")

    def _handle_completion(self):
        if self.global_remaining_time <= 0 < self.bonus_credits:
            self.claim_bonus_button.setEnabled(True)
            self.claim_bonus_button.show()
        AudioCue("resources/audio/timer_end.wav")
        self._show_message("Great job! You completed your study session!", True)

    def _show_message(self, message, is_mute):
        if not is_mute:
            AudioCue("resources/audio/notification.wav")
        self.toast = ToastNotifier(message)


    def _show_warning(self, message):
        AudioCue("resources/audio/warning.wav")
        self.toast = ToastNotifier(message)


    def _confirm_dialog(self, title, message):
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def update_credits_display(self):
        """Update the credits label with the current total credits."""
        self.credits_label.setText(f"Wealth: {self.flow_cred_system.get_total_credits()}")

    def update_timer(self):
        """Update the timer based on session or break status."""
        if not self.is_running:
            return

        if self.in_break:
            self._handle_break_time()
        elif not self.is_paused:
            self._handle_session_time()

    def _handle_break_time(self):
        """Handle the logic for the break timer."""
        self.break_time -= 1
        self._update_credits_and_display()

        if self.break_time <= 0:
            self.end_break()
        else:
            self.update_timer_label()

    def _handle_session_time(self):
        """Handle the logic for the session timer."""
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.global_remaining_time -= 1
            self._update_credits_and_display()

            if self.remaining_time <= 0:
                self.completed_intervals += 1
                if self.completed_intervals < self.pomodoro_count.value():
                    self.trigger_auto_break()
                else:
                    self.end_session()
        else:
            self.end_session()

    def _update_credits_and_display(self):
        """Update credits and UI elements during each timer tick."""
        self.flow_cred_system.update_credits(CREDITS_PER_SECOND)
        self.update_credits_display()
        self.update_timer_label()

    def update_timer_label(self):
        """Update the timer label to show the correct time."""
        if self.in_break:
            self.timer_label.setText(f"{self.break_time // 60:02}:{self.break_time % 60:02}")
        else:
            hours, remainder = divmod(self.global_remaining_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.timer_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")

    # Input Handling
    def show_time_inputs(self):
        """Show input fields for configuring session."""
        self.pomodoro_duration.show()
        self.pomodoro_count.show()
        self.configure_button.setText("Confirm")
        self.configure_button.clicked.connect(self.confirm_configuration)
        self.configuration_confirmed.emit()

    def confirm_configuration(self):
        """Hide input fields after confirming session configuration."""
        self.hide_time_inputs()
        self.configure_button.setText("Configure Session")
        self._reconnect_button(self.configure_button, self.show_time_inputs)

    def hide_time_inputs(self):
        """Hide input fields for session configuration."""
        self.pomodoro_duration.hide()
        self.pomodoro_count.hide()

    @staticmethod
    def _reconnect_button(button, new_function):
        """Reconnect button to a new function."""
        button.clicked.disconnect()
        button.clicked.connect(new_function)

    def start_cancel_session(self):
        """Start or cancel the session based on the current state."""
        if self.is_running:
            self.is_running = False
            self.start_button.setText("Start")
            self.interrupt_session()
        elif self.pomodoro_duration.value() != 0:
            self.is_running = True
            self.start_button.setText("Cancel")
            self.start_session()
        else:
            self._show_warning("Invalid Configuration!")

    def pause_resume_session(self):
        """Toggle between pause and resume states."""
        if self.is_paused:
            self.is_paused = False
            self.pause_resume_button.setText("Pause")
            self.timer.start(1000)
        else:
            self.is_paused = True
            self.pause_resume_button.setText("Resume")
            self.timer.stop()

    # Wealth and Bonus Handling
    def claim_bonus(self):
        """Claim the bonus credits and update the display."""
        self.flow_cred_system.update_credits(self.bonus_credits)
        self.update_credits_display()
        self.bonus_credits = 0
        self._hide_bonus_ui()
        self._show_message("You have claimed your bonus credits!", False)

    def update_bonus_label(self):
        """Update the bonus label with the current bonus information."""
        bonus_percentage = (self.bonus_multiplier - 1) * 100
        self.bonus_label.setText(f"(+{bonus_percentage:.2f}%) Bonus: {int(self.bonus_credits)}")

    def _hide_bonus_ui(self):
        """Hide the bonus UI elements after claiming the bonus."""
        self.bonus_label.hide()
        self.claim_bonus_button.hide()

    @staticmethod
    def calculate_bonus(duration):
        """Calculate bonus multiplier based on the duration."""
        if duration > 1:
            return 1 + (2 * duration ** 2) / (100 + 2 * duration ** 2)
        return 1

    def update_after_rent(self, message):
        """Update credits after renting the app and display a message."""
        self._show_message(message, False)
        self.update_credits_display()


class ToastNotifier(QWidget):
    active_toasts = []  # List to keep track of active toasts

    def __init__(self, message, duration=5000, parent=None):
        super().__init__(parent)

        self.setObjectName("toast")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                           Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.Popup)

        # Frosted glass effect using transparent background and overlay gradient
        self.setStyleSheet(style_sheet)

        layout = QVBoxLayout()
        self.label = QLabel(message)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.close)
        self.timer.start(duration)

        self.adjustSize()
        self.move_to_bottom_right()
        self.display()

        ToastNotifier.active_toasts.append(self)

    def move_to_bottom_right(self):
        """Position the toast in the bottom-right corner of the primary screen."""
        screen_geometry = QApplication.primaryScreen().geometry()
        y = screen_geometry.height() - self.height() - 100 - (len(ToastNotifier.active_toasts) - 1) * (self.height() + 10)
        x = screen_geometry.width() - self.width() - 20
        self.move(x, y)

    def display(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        """Override closeEvent to remove this toast from the active toasts list."""
        ToastNotifier.active_toasts.remove(self)
        event.accept()


class VaultWidget(QWidget):
    def __init__(self, app_manager: 'AppManager', wallet: 'Wallet'):
        super().__init__()
        self.list_widget = None
        self.app_manager = app_manager
        self.wallet = wallet
        self.scan_window = None
        self.setup_ui()
        self.connect_signals()
        self.refresh_vaulted_apps()

    def setup_ui(self):
        self.setWindowTitle("Vaulted Apps")

        main_layout = QVBoxLayout(self)

        self.list_widget = QListWidget(self)
        main_layout.addWidget(self.list_widget)
        hbutton_layout = QHBoxLayout()
        hbuttons = [
            ("Rent Selected", self.rent_selected_app),
            ("Unvault Selected", self.unvault_selected_app)
        ]
        for label, method in hbuttons:
            button = QPushButton(label, self)
            button.clicked.connect(method)
            hbutton_layout.addWidget(button)

        vbutton_layout = QVBoxLayout()
        self.open_sw_button = QPushButton("Vault App")
        self.open_sw_button.clicked.connect(self.open_scan_window)
        vbutton_layout.addWidget(self.open_sw_button)

        main_layout.addLayout(hbutton_layout)
        main_layout.addLayout(vbutton_layout)
        self.setLayout(main_layout)

    def _show_message(self, message, is_mute):
        if not is_mute:
            AudioCue("resources/audio/notification.wav")
        self.toast = ToastNotifier(message)
        self.toast.display()



    def _show_warning(self, message):
        AudioCue("resources/audio/warning.wav")
        self.toast = ToastNotifier(message)
        self.toast.display()


    def connect_signals(self):
        signals = [
            (self.app_manager.app_vaulted_signal, self.refresh_vaulted_apps),
            (self.app_manager.app_unvaulted_signal, self.refresh_vaulted_apps),
            (self.app_manager.rental_expired_signal, self.handle_rental_expiration)
        ]
        for signal, slot in signals:
            signal.connect(slot)

    def rent_selected_app(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            self._show_warning("Please select an app to rent.")
            return

        app_name = selected_items[0].text()

        credits_per_minute = 120
        rent_dialog = RentDialog(credits_per_minute, self.wallet)

        if rent_dialog.exec() == QDialog.DialogCode.Accepted:
            duration_minutes, total_price = rent_dialog.get_duration_and_price()
            self.app_manager.rent_app(app_name, duration_minutes)
            self.refresh_vaulted_apps()

    def unvault_selected_app(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            self._show_warning("Please select an app to unvault.")
            return

        app_name = selected_items[0].text()
        self.app_manager.unvault_app(app_name)
        self.refresh_vaulted_apps()

    def manual_add_app(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select App to Vault", "", "Executables (*.exe);;All Files (*)"
        )
        if file_path and os.path.exists(file_path):
            app_name = os.path.basename(file_path)
            name = app_name.removesuffix('.exe')
            reply = QMessageBox.question(
                self,
                f"Are you sure you want to vault {name}?",
                f"{name} will be permanently blocked unless unvaulted or rented.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.app_manager.vault_app(app_name)
                self.refresh_vaulted_apps()
            else:
                return

    def open_scan_window(self):
        """Open the system app scanner window."""

        if self.scan_window and self.scan_window.isVisible():
            self.scan_window.activateWindow()
            return
        if self.scan_window is not None:
            self.scan_window = None
        try:
            file_manager = FileManager()
            self.scan_window = ScanWindow(self, file_manager)
            self.scan_window.show()
            self.scan_window.destroyed.connect(self.on_scan_window_closed)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create scan window: {str(e)}")

    def on_scan_window_closed(self):
        self.scan_window = None

    def refresh_vaulted_apps(self):
        self.app_manager.load_data()

        self.list_widget.clear()

        for app_name, app_data in self.app_manager.vaulted_apps.items():
            item = QListWidgetItem(app_name)
            if app_data['is_rented']:
                item.setBackground(Qt.GlobalColor.gray)
            self.list_widget.addItem(item)

    def handle_rental_expiration(self, message):
        self._show_warning(message)


class FloatingToolbar(QWidget):
    def __init__(self, app_ui_instance=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet(style_sheet)
        self.app_ui = app_ui_instance
        self.libgen_window = None  # To keep track of the LibGen window instance
        self.init_ui()

        if self.app_ui:
            self.app_ui.windowShown.connect(self.on_window_shown)
            self.app_ui.windowHidden.connect(self.on_window_hidden)

        self.dragging = False
        self.drag_position = None

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(35)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 100))

        self.drag_button = QPushButton("")
        self.drag_button.setIcon(QIcon("resources/icons/drag.png"))
        self.drag_button.setFixedSize(24, 24)
        self.drag_button.setIconSize(QSize(24, 24))
        self.drag_button.setGraphicsEffect(shadow)
        self.drag_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drag_button.clicked.connect(lambda: None)
        layout.addWidget(self.drag_button)

        self.eye_button = QPushButton("")
        self.eye_button.setIcon(QIcon("resources/icons/o_eye.png"))
        self.eye_button.clicked.connect(self.toggle_visibility)
        self.eye_button.setObjectName("bubble")
        self.eye_button.setGraphicsEffect(shadow)
        self.eye_button.setIconSize(QSize(24, 24))
        layout.addWidget(self.eye_button)

        self.vault_button = QPushButton("")
        self.vault_button.setIcon(QIcon("resources/icons/lock-alt.png"))
        self.vault_button.clicked.connect(self.toggle_vault_visibility)
        self.vault_button.setObjectName("bubble")
        self.vault_button.setGraphicsEffect(shadow)
        self.vault_button.setIconSize(QSize(24, 24))
        layout.addWidget(self.vault_button)



        self.libgen_button = QPushButton("")
        self.libgen_button.setIcon(QIcon("resources/icons/book.png"))
        self.libgen_button.setCheckable(True)  # Make the button checkable
        self.libgen_button.clicked.connect(self.toggle_libgen)
        self.libgen_button.setObjectName("bubble")
        self.libgen_button.setGraphicsEffect(shadow)
        self.libgen_button.setIconSize(QSize(24, 24))
        self.libgen_button.setEnabled(False)
        #layout.addWidget(self.libgen_button)



        self.setLayout(layout)

        self.drag_button.mousePressEvent = self.mousePressEvent
        self.drag_button.mouseMoveEvent = self.mouseMoveEvent
        self.drag_button.mouseReleaseEvent = self.mouseReleaseEvent

    def mousePressEvent(self, event):
        """Handle mouse press event to start dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move event to drag the toolbar."""
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Handle mouse release event to stop dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()

    def toggle_libgen(self):
        """Toggle the LibGen window visibility."""
        if self.libgen_window is None:
            # Create and show the LibGen window if it doesn't exist
            self.libgen_window = LibGenWindow(self.app_ui)
            self.libgen_window.destroyed.connect(self.on_libgen_window_closed)  # Track when the window is closed
            self.libgen_window.show()  # Show the window
            self.libgen_button.setChecked(True)  # Mark the button as checked
        else:
            # If the window is already open, just toggle its visibility
            if self.libgen_window.isVisible():
                self.libgen_window.hide()  # Hide the window
                self.libgen_button.setChecked(False)  # Mark the button as unchecked
            else:
                self.libgen_window.show()  # Show the window again
                self.libgen_button.setChecked(True)  # Mark the button as checked

    def toggle_vault_visibility(self):
        """Toggle the visibility of the vault widget and adjust window size."""
        if self.app_ui.vault_widget.isVisible():
            self.app_ui.vault_widget.setVisible(False)
        else:
            self.app_ui.vault_widget.setVisible(True)

        self.app_ui.adjust_size()

    def toggle_visibility(self):
        """Toggle visibility of the main window."""
        if self.app_ui.isVisible():
            self.app_ui.hide()  # Hide the main window
            self.eye_button.setIcon(QIcon("resources/icons/close-eye.png"))  # Change to eye closed icon
        else:
            self.app_ui.show_window()  # Show the main window
            self.eye_button.setIcon(QIcon("resources/icons/o_eye.png"))

    def on_libgen_window_closed(self):
        """Handle the closure of the LibGen window."""
        self.libgen_window = None
        self.libgen_button.setChecked(False)

    def move_toolbar(self):
        """Update the position of the toolbar to the top right corner of the desktop."""
        screen_geometry = QApplication.primaryScreen().geometry()
        toolbar_x = screen_geometry.width() - self.width()  # Right side of the screen
        toolbar_y = 0  # Top of the screen
        self.move(toolbar_x, toolbar_y)

    def on_window_shown(self):
        self.eye_button.setIcon(QIcon("resources/icons/o_eye.png"))  # Eye open icon

    def on_window_hidden(self):
        self.eye_button.setIcon(QIcon("resources/icons/close-eye.png"))


class AppUI(QWidget):
    windowShown = pyqtSignal()
    windowHidden = pyqtSignal()
    def __init__(self):
        super().__init__()

        self.setStyleSheet(style_sheet)
        self.libgen_window = None
        self.tray_icon = QSystemTrayIcon(self)
        self.setWindowTitle("Flow Factory Incorporated")
        self.setWindowIcon(QIcon("resources/icons/FFInc Icon.png"))
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        self.file_manager = FileManager()
        self.l_on_start = LaunchOnStartQuery(self.file_manager)
        self.start_app_on_startup()

        self.wallet = Wallet(self.file_manager)
        self.app_manager = AppManager(self.file_manager, self.wallet)

        self.timer_app = TimerApp(self.wallet, self.app_manager)
        self.timer_app.configuration_confirmed.connect(self.adjust_size)
        self.vault_widget = VaultWidget(self.app_manager, self.wallet)
        self.vault_widget.setVisible(False)

        #self.libgen = Scraper()

        self.timer_app.setFixedSize(430, 275)
        self.vault_widget.setFixedSize(430, 400)

        self.timer_app.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.vault_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.timer_app)
        main_layout.addWidget(self.vault_widget)

        main_layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(main_layout)

        self.init_tray_icon()

        self.floating_toolbar = FloatingToolbar(app_ui_instance=self)
        self.floating_toolbar.show()
        self.floating_toolbar.move_toolbar()

    def adjust_size(self):
        self.layout().invalidate()
        self.adjustSize()



    def revert_to_initial_size(self):
        """Revert the window to its initialized size."""
        self.resize(self.initial_size)

    def init_tray_icon(self):
        """Initialize the system tray icon and its menu."""
        self.tray_icon.setIcon(QIcon("resources/icons/FFInc Icon.png"))

        tray_menu = QMenu()

        quit_action = QAction(QIcon('resources/icons/cross.png'), "Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        """Handle tray icon activation (left click to restore window)."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()

    def show_window(self):
        """Restore and show the application window."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def start_app_on_startup(self):
        """Start the application on system startup."""
        if self.file_manager.is_first_launch():
            self.l_on_start.exec()
            self.file_manager.set_first_launch_done()
            self.l_on_start.add_to_startup()
            self.toast = ToastNotifier("Added Flow Factory to startup.", False)

    @staticmethod
    def quit_app():
        """Quit the application completely."""
        QApplication.quit()

    def closeEvent(self, event):
        """Handle the window close event by minimizing to tray."""
        if self.isMinimized() or not self.isVisible():
            event.ignore()
        else:
            self.windowHidden.emit()
            event.ignore()
            self.hide()
    def showEvent(self, event):
        """Handle the window show event."""
        self.windowShown.emit()
        event.accept()


class ScanWindow(QMainWindow):
    def __init__(self, vault_window, file_manager):
        super().__init__()
        try:
            self.setStyleSheet(style_sheet)
            self.setWindowTitle("System App Scanner")
            self.setGeometry(100, 100, 400, 400)
            self.setWindowFlags(
                Qt.WindowType.Tool)
            self.scanner = SystemAppScanner()
            self.app_manager = AppManager(file_manager, Wallet(file_manager))
            self.app_list_widget = AppListWidget(self.scanner, self.app_manager, vault_window, file_manager)
            self.app_list_widget._scan_apps(force_refresh=True)
            self.setCentralWidget(self.app_list_widget)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"An error occurred: {str(e)}")
            self.close()


if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    QFontDatabase.addApplicationFont("resources/font/FeatureMono-Bold.ttf")
    app.setWindowIcon(QIcon("resources/icons/FFInc Icon.png"))
    app.setApplicationName("Flow Factory Incorporated")
    app.setOrganizationName("Aymen Moujtahid")
    app.setOrganizationDomain("https://github.com/boehm-or-the-egg/FFinc./releases/tag/v.02-alpha.com")
    file_manager = FileManager()
    window = AppUI()
    window.show()
    sys.exit(app.exec())

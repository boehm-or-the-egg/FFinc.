import os
import sys
import threading
import time

import psutil
from PyQt6.QtCore import QTimer, Qt, pyqtSlot, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QFont, QFontDatabase, QAction
from PyQt6.QtWidgets import (QMainWindow, QListWidget, QVBoxLayout, QWidget, QLineEdit, QListWidgetItem, QPushButton,
                             QMessageBox, QDialog, QSpinBox, QLabel, QHBoxLayout, QFileDialog, QApplication,
                             QSystemTrayIcon, QMenu, QSizePolicy, QCheckBox)

from file_manager import FileManager

CREDITS_PER_SECOND = 3
CREDITS_SAVE_FILE = "../app_data.json"
CHECK_INTERVAL_RUNNING = 5
UNVAULT_FEE = 120000
SIZE_THRESHOLD = 2048 * 1024
TIMESTEP = 1


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


class AppListWidget(QWidget):
    # noinspection PyUnresolvedReferences
    def __init__(self, scanner, app_manager, vault_window, file_manager):
        super().__init__()
        self.flow_cred_system = FlowCredSystem(file_manager)
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

        self.add_to_vault_button = QPushButton("Add to Vault", self)
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
                QMessageBox.warning(self, "Warning", "No application selected to add to vault.")
                return

            for item in selected_items:
                exe_path = item.data(Qt.ItemDataRole.UserRole)
                app_name = os.path.basename(exe_path)

                if not exe_path or not os.path.exists(exe_path):
                    QMessageBox.warning(self, "Error", f"The application '{app_name}' does not exist.")
                    continue

                try:
                    reply = QMessageBox.question(
                        self,
                        "Vault App",
                        f"Are you sure you want to vault {app_name}? {app_name} will be permanently blocked unless unvaulted or rented.",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        self.app_manager.vault_app(app_name)
                        self.vault_window.refresh_vaulted_apps()
                    else:
                        return
                except Exception as e:
                    QMessageBox.warning(self, "Error Adding App", f"Failed to add {app_name} to the vault: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while adding to vault: {str(e)}")

    @pyqtSlot(str)
    def on_app_rented(self, message):
        """Handle rental status messages."""
        QMessageBox.information(self, "Rental Status", message)


class ScanWindow(QMainWindow):
    def __init__(self, vault_window, file_manager):
        super().__init__()
        try:
            self.setWindowTitle("System App Scanner")
            self.setGeometry(100, 100, 400, 400)
            self.scanner = SystemAppScanner()
            self.app_manager = AppManager(file_manager, FlowCredSystem(file_manager))
            self.app_list_widget = AppListWidget(self.scanner, self.app_manager, vault_window, file_manager)
            self.app_list_widget._scan_apps(force_refresh=True)
            self.setCentralWidget(self.app_list_widget)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"An error occurred: {str(e)}")
            self.close()


# noinspection PyUnresolvedReferences
class AppManager(QObject):
    DATA_FILE = '../app_data.json'
    app_rented_signal = pyqtSignal(str)
    app_vaulted_signal = pyqtSignal(str)
    app_unvaulted_signal = pyqtSignal(str)
    rental_expired_signal = pyqtSignal(str)

    def __init__(self, file_manager, flow_cred_system: 'FlowCredSystem'):
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

            rental_cost = duration_minutes * 120
            if self.flow_cred_system.get_total_credits() < rental_cost:
                self.app_rented_signal.emit("You do not have enough credits to rent this app.")
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


class FlowCredSystem:
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


# noinspection PyUnresolvedReferences
class TimerApp(QWidget):

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

        self.credits_label = QLabel(f"Wealth: {self.flow_cred_system.get_total_credits()}")
        self.layout.addWidget(self.credits_label)

        self.credits_label.setStyleSheet("font-size: 24px;")
        timer_layout = QHBoxLayout()
        self.setWindowTitle("Study Timer")
        self.layout.addWidget(self.timer_label)
        self.timer_label.setStyleSheet("font-size: 72px;")
        self.layout.addLayout(timer_layout)
        self.bonus_label.setStyleSheet("font-size: 18px;")
        self.bonus_label.hide()
        self.layout.addWidget(self.bonus_label)

        self.claim_bonus_button.setEnabled(False)
        self.claim_bonus_button.hide()
        self.claim_bonus_button.clicked.connect(self.claim_bonus)
        self.layout.addWidget(self.claim_bonus_button)

        self.pomodoro_duration.setRange(0, 120)
        self.pomodoro_duration.setSingleStep(TIMESTEP)
        self.pomodoro_duration.setPrefix("Pomodoro duration: ")
        self.pomodoro_count.setRange(1, 12)
        self.pomodoro_count.setPrefix("Count: ")
        self.pomodoro_count.setValue(2)
        self.pomodoro_duration.setMinimumWidth(230)
        self.pomodoro_count.setMinimumWidth(130)
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.pomodoro_duration)
        time_layout.addWidget(self.pomodoro_count)

        self.layout.addLayout(time_layout)
        self.hide_time_inputs()

        self.configure_button.clicked.connect(self.show_time_inputs)
        self.layout.addWidget(self.configure_button)

        button_layout = QHBoxLayout()
        self.start_button.clicked.connect(self.start_cancel_session)
        button_layout.addWidget(self.start_button)

        self.pause_resume_button.clicked.connect(self.pause_resume_session)
        self.pause_resume_button.setEnabled(False)
        button_layout.addWidget(self.pause_resume_button)
        self.skip_break.stateChanged.connect(self.is_skip_break)
        button_layout.addWidget(self.skip_break)

        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)

        self.timer.timeout.connect(self.update_timer)

    def is_skip_break(self,state):
        return state == Qt.CheckState.Checked

    def update_credits_display(self):
        self.credits_label.setText(f"Wealth: {self.flow_cred_system.get_total_credits()}")

    def show_time_inputs(self):
        self.pomodoro_duration.show()
        self.pomodoro_count.show()
        self.configure_button.setText("Confirm")
        self.configure_button.clicked.connect(self.confirm_configuration)

    def confirm_configuration(self):
        self.hide_time_inputs()
        self.configure_button.setText("Configure Session")
        self.configure_button.clicked.disconnect()
        self.configure_button.clicked.connect(self.show_time_inputs)

    def hide_time_inputs(self):
        self.pomodoro_duration.hide()
        self.pomodoro_count.hide()

    def trigger_auto_break(self):
        self.in_break = True
        self.break_time = int(self.pomodoro_duration.value() * 60 * 0.2)
        self.update_timer_label()
        self.timer.start(1000)
        QMessageBox.information(self, "Pomodoro Complete",
                                "Good Work! I started a break for you, make sure you use it to your advantage.")
    def end_break(self):
        self.in_break = False
        self.start_next_subsession()

    def start_next_subsession(self):
        if self.completed_intervals < self.pomodoro_count.value():
            self.remaining_time = self.pomodoro_duration.value() * 60
            self.update_timer_label()
        else:
            self.end_session()

    def start_session(self):
        session_duration = self.pomodoro_duration.value() * 60
        total_duration = session_duration * self.pomodoro_count.value()

        if session_duration <= 0:
            QMessageBox.warning(self, "Invalid Input", "Please select a non-zero time.")
            return

        self.auto_pause_duration = session_duration * 0.2
        self.remaining_time = session_duration
        self.global_remaining_time = total_duration
        self.session_completed = False

        self.claim_bonus_button.setEnabled(False)
        self.configure_button.setEnabled(False)
        self.claim_bonus_button.hide()
        self.bonus_label.hide()

        if total_duration > 3600:
            self.bonus_multiplier = self.calculate_bonus(total_duration / 3600)
            self.bonus_credits = (total_duration + (self.auto_pause_duration * (self.pomodoro_count.value() - 1))) * (
                    self.bonus_multiplier - 1)
            self.update_bonus_label()
            self.bonus_label.show()
        else:
            self.bonus_multiplier = 1.0
            self.bonus_credits = 0

        self.update_timer_label()
        self.is_running = True
        self.is_paused = False
        self.pause_resume_button.setEnabled(True)

        self.timer.start(1000)

    def update_timer(self):
        if self.is_running:
            if self.in_break:
                self.break_time -= 1
                self.flow_cred_system.update_credits(CREDITS_PER_SECOND)
                self.update_credits_display()
                self.update_timer_label()
                if self.break_time <= 0:
                    self.end_break()
            elif self.remaining_time > 0 and not self.is_paused:
                self.remaining_time -= 1
                self.global_remaining_time -= 1
                self.update_timer_label()
                self.flow_cred_system.update_credits(CREDITS_PER_SECOND)
                self.update_credits_display()

                if self.remaining_time <= 0:
                    self.completed_intervals += 1
                    if self.completed_intervals < self.pomodoro_count.value():
                        self.trigger_auto_break()
                    else:
                        self.end_session()
            else:
                self.end_session()

    def end_session(self, interrupted=False):
        self.timer.stop()
        self.is_running = False
        self.start_button.setText("Start")
        self.pause_resume_button.setEnabled(False)
        self.configure_button.setEnabled(True)

        if interrupted:
            self.bonus_label.hide()
            self.claim_bonus_button.hide()
            QMessageBox.information(self, "Session Interrupted",
                                    "Your session was interrupted. No bonus will be applied.")
        else:
            if self.global_remaining_time <= 0:
                if self.bonus_credits > 0:
                    self.claim_bonus_button.setEnabled(True)
                    self.claim_bonus_button.show()

            QMessageBox.information(self, "Session Complete", "Great job! You completed your study session!")

    def claim_bonus(self):

        self.flow_cred_system.update_credits(self.bonus_credits)
        self.update_credits_display()
        self.bonus_credits = 0
        self.bonus_label.hide()
        self.claim_bonus_button.hide()
        QMessageBox.information(self, "Bonus Claimed", "You have claimed your bonus credits!")

    def interrupt_session(self):
        reply = QMessageBox.question(self, "Interrupt Session",
                                     "Are you sure you want to interrupt the session?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.end_session(interrupted=True)

    def update_bonus_label(self):
        self.bonus_label.setText(f"(+{(self.bonus_multiplier - 1) * 100:.2f}%) Bonus: {int(self.bonus_credits)}")

    def update_timer_label(self):
        if self.in_break:
            self.timer_label.setText(f"Break: {self.break_time // 60:02}:{self.break_time % 60:02}")
        else:
            hours, remainder = divmod(int(self.global_remaining_time), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.timer_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")

    def start_cancel_session(self):
        if self.is_running:
            self.is_running = False
            self.start_button.setText("Start")
            self.interrupt_session()
        elif self.pomodoro_duration.value() != 0:
            self.is_running = True
            self.start_button.setText("Cancel")
            self.start_session()
        else:
            QMessageBox.warning(self, "Error", "Session is not properly configured.")

    def pause_resume_session(self):
        if self.is_paused:
            self.is_paused = False
            self.pause_resume_button.setText("Pause")
            self.timer.start(1000)
        else:
            self.is_paused = True
            self.pause_resume_button.setText("Resume")
            self.timer.stop()

    def update_after_rent(self, message):
        QMessageBox.information(self, "App Rented", message)
        self.update_credits_display()

    @staticmethod
    def calculate_bonus(duration):
        if duration > 1:
            return 1 + (2 * duration ** 2) / (100 + 2 * duration ** 2)
        else:
            return 1


# noinspection PyUnresolvedReferences
class RentDialog(QDialog):
    def __init__(self, credits_per_minute, flow_cred_system, parent=None):
        super().__init__(parent)
        self.credits_per_minute = credits_per_minute
        self.current_price = 0
        self.flow_cred_system = flow_cred_system
        self.available_credits = self.flow_cred_system.get_total_credits()

        layout = QVBoxLayout()

        self.instruction_label = QLabel("Select the duration in minutes:")
        layout.addWidget(self.instruction_label)

        self.time_spinner = QSpinBox()
        self.time_spinner.setSuffix(" m")
        self.time_spinner.setRange(5, 120)
        self.time_spinner.setValue(5)
        layout.addWidget(self.time_spinner)

        self.price_label = QLabel(f"Price: {self.current_price} FlowCreds")
        layout.addWidget(self.price_label)

        self.balance_label = QLabel(f"Available Credits: {self.available_credits} FlowCreds")
        layout.addWidget(self.balance_label)

        self.time_spinner.valueChanged.connect(self.update_price_and_balance)

        self.confirm_button = QPushButton("Rent")
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)

        self.setLayout(layout)

        self.update_price_and_balance()

    def update_price_and_balance(self):
        """Update the price label and check if the user has enough credits."""
        time_in_minutes = self.time_spinner.value()
        self.current_price = time_in_minutes * self.credits_per_minute
        self.price_label.setText(f"Price: {self.current_price} FlowCreds")

        self.available_credits = self.flow_cred_system.get_total_credits()
        self.balance_label.setText(f"Available Credits: {self.available_credits} FlowCreds")

        if self.current_price > self.available_credits:
            self.price_label.setStyleSheet("color: red;")
            self.confirm_button.setEnabled(False)
        else:
            self.price_label.setStyleSheet("color: default;")
            self.confirm_button.setEnabled(True)

    def get_duration_and_price(self):
        """Return the selected duration and price."""
        return self.time_spinner.value(), self.current_price


# noinspection PyUnresolvedReferences
class VaultWidget(QWidget):
    def __init__(self, app_manager: 'AppManager', flow_cred_system: 'FlowCredSystem'):
        super().__init__()
        self.list_widget = None
        self.app_manager = app_manager
        self.flow_cred_system = flow_cred_system
        self.scan_window = None
        self.setup_ui()
        self.connect_signals()
        self.refresh_vaulted_apps()

    def setup_ui(self):
        self.setWindowTitle("Vaulted Apps")
        self.list_widget = QListWidget(self)
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)

        buttons = [
            ("Rent Selected", self.rent_selected_app),
            ("Unvault Selected", self.unvault_selected_app),
            ("Manually Add App", self.manual_add_app),
            ("Add Running App", self.open_scan_window)
        ]

        for label, method in buttons:
            button = QPushButton(label, self)
            button.clicked.connect(method)
            layout.addWidget(button)

        self.setLayout(layout)

    def connect_signals(self):
        signals = [
            (self.app_manager.app_vaulted_signal, self.refresh_vaulted_apps),
            (self.app_manager.app_unvaulted_signal, self.refresh_vaulted_apps),
            (self.app_manager.rental_expired_signal, self.handle_rental_expiration)
        ]
        for signal, slot in signals:
            signal.connect(slot)

    @pyqtSlot(str)
    def on_app_vaulted(self):
        self.refresh_vaulted_apps()

    def rent_selected_app(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Error", "Please select an app to rent.")
            return

        app_name = selected_items[0].text()

        credits_per_minute = 120
        rent_dialog = RentDialog(credits_per_minute, self.flow_cred_system)

        if rent_dialog.exec() == QDialog.DialogCode.Accepted:
            duration_minutes, total_price = rent_dialog.get_duration_and_price()
            self.app_manager.rent_app(app_name, duration_minutes)
            self.refresh_vaulted_apps()

    def unvault_selected_app(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Error", "Please select an app to unvault.")
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
            reply = QMessageBox.question(
                self,
                "Vault App",
                f"Are you sure you want to vault {app_name}? {app_name} will be permanently blocked unless unvaulted or rented.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.app_manager.vault_app(app_name)
                self.refresh_vaulted_apps()
            else:
                return

    def open_scan_window(self):
        if self.scan_window is None or not self.scan_window.isVisible():
            file_manager = FileManager()
            self.scan_window = ScanWindow(self, file_manager)
            self.scan_window.show()
        else:
            self.scan_window.activateWindow()

    def refresh_vaulted_apps(self):
        self.app_manager.load_data()

        self.list_widget.clear()

        for app_name, app_data in self.app_manager.vaulted_apps.items():

            item = QListWidgetItem(app_name)
            if app_data['is_rented']:
                item.setBackground(Qt.GlobalColor.yellow)
            else:
                item.setText(app_name)

            self.list_widget.addItem(item)

    def handle_rental_expiration(self, message):
        QMessageBox.warning(self, "Rental Expiration", message)


# noinspection PyUnresolvedReferences
class AppUI(QWidget):
    def __init__(self):
        super().__init__()

        self.initial_size = self.sizeHint()

        self.tray_icon = QSystemTrayIcon(self)
        self.setWindowTitle("Flow Factory Incorporated")
        self.setWindowIcon(QIcon("joe.png"))
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint)

        self.file_manager = FileManager()
        self.flow_cred_system = FlowCredSystem(self.file_manager)
        self.app_manager = AppManager(self.file_manager, self.flow_cred_system)

        self.timer_app = TimerApp(self.flow_cred_system, self.app_manager)
        self.vault_widget = VaultWidget(self.app_manager, self.flow_cred_system)
        self.vault_widget.setVisible(False)

        self.vault_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.timer_app.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        button_toggle_vault = QPushButton("Toggle Vault")
        button_toggle_vault.clicked.connect(self.toggle_vault_visibility)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.timer_app)
        main_layout.addWidget(button_toggle_vault)
        main_layout.addWidget(self.vault_widget)

        self.setLayout(main_layout)

        self.init_tray_icon()

    def toggle_vault_visibility(self):
        """Toggle the visibility of the vault widget and adjust window size."""
        if self.vault_widget.isVisible():
            self.vault_widget.setVisible(False)
        else:
            self.vault_widget.setVisible(True)

        self.adjustSize()
        self.updateGeometry()

    def revert_to_initial_size(self):
        """Revert the window to its initialized size."""
        self.resize(self.initial_size)

    def init_tray_icon(self):
        """Initialize the system tray icon and its menu."""
        self.tray_icon.setIcon(QIcon("joe.png"))

        tray_menu = QMenu()

        quit_action = QAction(QIcon('cross.png'), "Quit", self)
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

    @staticmethod
    def quit_app():
        """Quit the application completely."""
        QApplication.quit()

    def closeEvent(self, event):
        """Handle the window close event by minimizing to tray."""
        if self.isMinimized() or not self.isVisible():
            event.ignore()
        else:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "App Running",
                "The app is minimized to the system tray. Click the icon to restore.",
                QSystemTrayIcon.MessageIcon.NoIcon,
                2000
            )




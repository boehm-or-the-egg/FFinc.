from PyQt6.QtWidgets import QWidget
from backup.FFInc.observer import Observer
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

class VaultWidget(QWidget, Observer):
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
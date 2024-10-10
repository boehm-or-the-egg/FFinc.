
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QVBoxLayout, QWidget,QPushButton,QApplication, QSystemTrayIcon, QMenu, QSizePolicy

from backup.FFInc.vault import VaultWidget
from backup.FFInc.wallet import Wallet
from backup.app import AppManager
from file_manager import FileManager

CREDITS_PER_SECOND = 3
CREDITS_SAVE_FILE = "../app_data.json"
CHECK_INTERVAL_RUNNING = 5
UNVAULT_FEE = 120000
SIZE_THRESHOLD = 2048 * 1024
TIMESTEP = 1


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
        self.wallet = Wallet(self.file_manager)
        self.app_manager = AppManager(self.file_manager, self.wallet)

        self.session_handler = Session(self.wallet, self.app_manager)
        self.vault_widget = VaultWidget(self.app_manager, self.wallet)
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
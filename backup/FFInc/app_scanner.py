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
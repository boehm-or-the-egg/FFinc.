import json
import os
import shutil
import threading


class FileManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one instance is created."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_file='app_data.json'):
        if self._initialized:
            return  # Skip initialization if already initialized

        self.data_file = data_file
        self.temp_file = f"{data_file}.tmp"
        self.lock = threading.Lock()

        self._initialized = True

    @staticmethod
    def _validate_json_data(data):
        """Ensures the required keys are present and initializes any missing ones."""
        default_structure = {
            'apps': {
                'vaulted_apps': {},
            },
            'credits': {
                'total_credits': 0
            }
        }

        # Recursively update missing keys with default values
        def recursive_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict):
                    d[k] = recursive_update(d.get(k, {}), v)
                else:
                    d.setdefault(k, v)
            return d

        return recursive_update(data, default_structure)

    def load_data(self):
        """Thread-safe load method."""
        with self.lock:
            if os.path.exists(self.data_file):
                try:
                    with open(self.data_file, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        return self._validate_json_data(data)
                except (json.JSONDecodeError, IOError):
                    return self._validate_json_data({})
            else:
                return self._validate_json_data({})

    def save_data(self, data):
        """Thread-safe, atomic save method."""
        with self.lock:
            # Ensure data is validated before saving
            data = self._validate_json_data(data)

            # Write to a temporary file first
            try:
                with open(self.temp_file, 'w', encoding='utf-8') as temp_file:
                    json.dump(data, temp_file, indent=4)
                shutil.move(self.temp_file, self.data_file)
            except IOError:
                return

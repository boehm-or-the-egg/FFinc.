from cx_Freeze import setup, Executable
import sys
import os

# Ensure that PyQt6 plugins (such as platforms) are included in the build
os.environ['QT_PLUGIN_PATH'] = os.path.join(sys.base_prefix, 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'plugins')

# Include necessary files (source and destination within the build directory)
include_files = [
    ('FeatureMono-Bold.ttf', 'FeatureMono-Bold.ttf'),  # Font file
    ('break.wav', 'break.wav'),                       # Sound file
    ('notification.wav', 'notification.wav'),         # Sound file
    ('timer_end.wav', 'timer_end.wav'),               # Sound file
    ('timer_start.wav', 'timer_start.wav'),           # Sound file
    ('warning.wav', 'warning.wav'),                   # Sound file
    ('FFInc Icon.png', 'FFInc Icon.png')              # App icon
]

# Additional options for cx_Freeze
build_exe_options = {
    'packages': ['os', 'sys', 'json', 'shutil', 'threading', 'time', 'psutil', 'pygame', 'PyQt6'],
    'include_files': include_files,
    'excludes': ['tkinter'],  # Exclude unnecessary modules if not used
    'includes': ['atexit', 're'],  # Some modules might need to be explicitly included
}

# The main entry point of your application
base = None
if sys.platform == 'win32':
    base = 'Win32GUI'  # Ensures no console window is shown when running the app on Windows

# Create the executable configuration
executable = Executable(
    script='ffinc.py',  # Your main script
    base=base,
    target_name='FFInc.exe',  # Name of the output executable
    icon='FFInc Icon.png'  # Path to your app's icon
)

# The actual setup call
setup(
    name='FFInc',
    version='0.02-alpha',
    description='Flow Factor Incorporated',
    options={'build_exe': build_exe_options},
    executables=[executable]
)

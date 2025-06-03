#!/usr/bin/env python3
import os
import glob # Added for wildcard searching

# Calculate the absolute path to the plugins directory
# Assuming the script is in 'src/' and plugins are in 'venv/lib/pythonX.Y/site-packages/cv2/qt/plugins/platforms'
# relative to the project root.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Dynamically find the pythonX.Y directory
python_version_dir_pattern = os.path.join(project_root, "venv", "lib", "python*")
python_version_dirs = glob.glob(python_version_dir_pattern)

qt_plugin_path = ""
if python_version_dirs:
    # Take the first match (should ideally be only one in a standard venv)
    python_version_dir = python_version_dirs[0]
    qt_plugin_path = os.path.join(python_version_dir, "site-packages", "cv2", "qt", "plugins", "platforms")
    # Note: opencv-python-headless doesn't have Qt plugins, so this path won't exist
    # os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = qt_plugin_path
else:
    print("Warning: Could not find pythonX.Y/site-packages path for Qt plugins.")

# Bỏ qua cảnh báo CSS không hỗ trợ
os.environ["QT_LOGGING_RULES"] = "qt.qpa.xcb.pci.propertymatch=false;*.debug=false;qt.qpa.xcb=false;qt.css.*=false"

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import main

if __name__ == "__main__":
    main()

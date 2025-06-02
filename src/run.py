#!/usr/bin/env python3
import os

# Calculate the absolute path to the plugins directory
# Assuming the script is in 'src/' and plugins are in 'venv/lib/python3.10/site-packages/cv2/qt/plugins/platforms'
# relative to the project root.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
qt_plugin_path = os.path.join(project_root, "venv", "lib", "python3.10", "site-packages", "cv2", "qt", "plugins", "platforms")

# Bỏ qua cảnh báo CSS không hỗ trợ
os.environ["QT_LOGGING_RULES"] = "qt.qpa.xcb.pci.propertymatch=false;*.debug=false;qt.qpa.xcb=false;qt.css.*=false"

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import main

if __name__ == "__main__":
    main()

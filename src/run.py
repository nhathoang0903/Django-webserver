#!/usr/bin/env python3
import os
# Bỏ qua cảnh báo CSS không hỗ trợ
os.environ["QT_LOGGING_RULES"] = "qt.qpa.xcb.pci.propertymatch=false;*.debug=false;qt.qpa.xcb=false;qt.css.*=false"

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import main

if __name__ == "__main__":
    main()

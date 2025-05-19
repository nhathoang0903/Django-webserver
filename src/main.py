import sys
import logging
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QIcon
from page1_welcome import WelcomePage
import subprocess
from utils.translation import set_language

# Bỏ qua cảnh báo CSS không hỗ trợ
os.environ["QT_LOGGING_RULES"] = "qt.qpa.xcb.pci.propertymatch=false;*.debug=false;qt.qpa.xcb=false;qt.css.*=false"

# Create logs directory if it doesn't exist
LOG_DIR = os.path.join(os.path.dirname(__file__), 'app', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Log file path and limit
APP_LOG = os.path.join(LOG_DIR, 'app.log')
APP_LOG_LIMIT = 100

class LogCleaner:
    @staticmethod
    def count_lines(file_path):
        try:
            with open(file_path, 'r') as f:
                return sum(1 for _ in f)
        except:
            return 0

    @staticmethod
    def clear_log(file_path):
        try:
            open(file_path, 'w').close()
            logging.info(f"Cleared log file: {file_path}")
        except Exception as e:
            logging.error(f"Failed to clear log file {file_path}: {e}")

    @staticmethod
    def check_and_clear_log():
        if os.path.exists(APP_LOG):
            if LogCleaner.count_lines(APP_LOG) >= APP_LOG_LIMIT:
                LogCleaner.clear_log(APP_LOG)

# Check and clear log before starting
LogCleaner.check_and_clear_log()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(APP_LOG),
        logging.StreamHandler()
    ]
)

class KioskApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        logging.info("Starting Cartsy Application")
        # Set application-wide attributes
        self.setOverrideCursor(Qt.BlankCursor)
        
        # Thiết lập ngôn ngữ mặc định là tiếng Việt
        set_language("vi")
        logging.info("Set default language to Vietnamese")
        
        # Hide taskbar on Raspberry Pi
        if os.path.exists('/usr/bin/lxpanel'):
            subprocess.run(['pkill', 'lxpanel'])
        
        # Set application icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))
    
    def show_main_window(self):
        self.main_window = WelcomePage()
        self.main_window.setWindowFlags(
            Qt.Window | 
            Qt.FramelessWindowHint |  # No window decorations
            Qt.WindowStaysOnTopHint   # Always on top
        )
        self.main_window.showFullScreen()
        self.main_window.move(QPoint(0, 0))  # Ensure window starts at (0,0)
        
        # Install event filter for Ctrl+X detection
        self.main_window.installEventFilter(self.main_window)
        
    def restore_system_state(self):
        logging.info("Restoring system state")
        # Show taskbar again on Raspberry Pi
        if os.path.exists('/usr/bin/lxpanel'):
            subprocess.Popen(['lxpanel', '--profile', 'LXDE-pi'])
            
def main():
    try:
        # Check log size before starting app
        LogCleaner.check_and_clear_log()
        
        app = KioskApplication(sys.argv)
        app.show_main_window()
        logging.info("Main window displayed")
        result = app.exec_()
        app.restore_system_state()
        sys.exit(result)
    except Exception as e:
        logging.error(f"Application error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

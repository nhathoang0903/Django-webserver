import sys
import logging
import os
import requests
import json
import signal
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPoint, QTimer, QEvent
from PyQt5.QtGui import QIcon
from page1_welcome import WelcomePage
import subprocess
from utils.translation import set_language
from config import DEVICE_ID, CART_END_SESSION_API

# Bỏ qua cảnh báo CSS không hỗ trợ
os.environ["QT_LOGGING_RULES"] = "qt.qpa.xcb.pci.propertymatch=false;*.debug=false;qt.qpa.xcb=false;qt.css.*=false"
os.environ["QT_QPA_PLATFORM"] = "xcb"  # For better performance on Linux
os.environ["QT_SCALE_FACTOR"] = "1"    # Prevent scaling issues

# Thêm cấu hình để tối ưu xử lý events
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

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
        
        # Thêm cấu hình để tăng responsive
        self.setAttribute(Qt.AA_EnableHighDpiScaling)
        self.setAttribute(Qt.AA_UseHighDpiPixmaps)
        
        # Tăng độ ưu tiên cho event processing
        self.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        
        # Tăng kích thước của event queue
        self.maxThreadCount = 4
        self.processEvents()
        
        # Thêm timer để đảm bảo UI responsive
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self.process_pending_events)
        self.process_timer.start(16)  # 60fps
        
        # Khởi tạo window chính
        self.main_window = None
        self.restore_system_state()
        
        # Thiết lập signal handler
        signal.signal(signal.SIGINT, self.cleanup_on_exit)
        signal.signal(signal.SIGTERM, self.cleanup_on_exit)
        
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
        
        # Register application exit handler
        self.aboutToQuit.connect(self.cleanup_on_exit)
    
    def process_pending_events(self):
        # Process pending events để tránh UI freeze
        self.processEvents()
        
    def event(self, event):
        # Override event handler để ưu tiên xử lý UI events
        if event.type() == QEvent.ApplicationStateChange:
            self.processEvents()
        return super().event(event)

    def cleanup_on_exit(self, sig, frame):
        """Ensure the cart session is properly ended when the application exits"""
        logging.info(f"Received signal {sig}, shutting down...")
        self.quit()
        
        logging.info("Application shutting down, cleaning up cart session...")
        try:
            # Call the end session API
            response = requests.post(f"{CART_END_SESSION_API}{DEVICE_ID}/", timeout=2)
            if response.status_code == 200:
                logging.info("Successfully ended cart session")
            else:
                logging.warning(f"Failed to end cart session: {response.status_code}, {response.text}")
        except Exception as e:
            logging.error(f"Error ending cart session: {e}")
        
        # Clear phone number in JSON file
        try:
            phone_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                    'config', 'phone_number.json')
            if os.path.exists(phone_path):
                with open(phone_path, 'w') as f:
                    json.dump({"phone_number": ""}, f)
                logging.info("Successfully cleared phone number")
        except Exception as e:
            logging.error(f"Error clearing phone number: {e}")
            
        # Clear cart data
        try:
            from cart_state import CartState
            cart_state = CartState()
            cart_state.clear_cart()
            logging.info("Successfully cleared cart state")
        except Exception as e:
            logging.error(f"Error clearing cart state: {e}")
    
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

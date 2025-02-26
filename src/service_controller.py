import subprocess
import sys
import os
import time
import signal
import logging
import requests
from config import SERVER_IP, SERVER_PORT, BASE_URL, DEVICE_ID

# Update app path
APP_DIR = os.path.join(os.path.dirname(__file__), 'app')
LOG_DIR = os.path.join(APP_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Log file paths and limits
SERVICE_LOG = os.path.join(LOG_DIR, 'service.log')
APP_LOG = os.path.join(LOG_DIR, 'app.log')
SERVICE_LOG_LIMIT = 3000
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
    def check_and_clear_logs():
        if os.path.exists(SERVICE_LOG):
            if LogCleaner.count_lines(SERVICE_LOG) >= SERVICE_LOG_LIMIT:
                LogCleaner.clear_log(SERVICE_LOG)
                
        if os.path.exists(APP_LOG):
            if LogCleaner.count_lines(APP_LOG) >= APP_LOG_LIMIT:
                LogCleaner.clear_log(APP_LOG)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(SERVICE_LOG),
        logging.StreamHandler()
    ]
)

from device_controller import DeviceController

class ServiceController:
    def __init__(self):
        self.device_controller = DeviceController()
        self.app_process = None
        self.running = True
        
    def start_app(self):
        if self.app_process is None:
            try:
                python_path = sys.executable
                # Update path to main.py
                app_path = os.path.join(os.path.dirname(__file__), "main.py")
                
                # Start process with proper environment
                env = os.environ.copy()
                env['DISPLAY'] = ':0'
                env['XAUTHORITY'] = os.path.expanduser('~/.Xauthority')
                
                self.app_process = subprocess.Popen(
                    [python_path, app_path],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                logging.info("App started successfully")
                self.device_controller.update_status(is_active=True, app_running=True)
            except Exception as e:
                logging.error(f"Failed to start app: {e}")
            
    def stop_app(self):
        if self.app_process:
            try:
                self.app_process.terminate()
                self.app_process.wait(timeout=5)  # Wait up to 5 seconds
                self.app_process = None
                logging.info("App stopped successfully")
            except Exception as e:
                logging.error(f"Error stopping app: {e}")
                # Force kill if terminate fails
                try:
                    self.app_process.kill()
                except:
                    pass
            finally:
                self.device_controller.update_status(is_active=True, app_running=False)
    
    def shutdown_device(self):
        self.stop_app()
        self.device_controller.update_status(is_active=False, app_running=False)
        os.system("sudo shutdown -h now")
        
    def run(self):
        # Initialize device status
        self.device_controller.update_status(is_active=True, app_running=False)
        logging.info("Service controller started...")
        
        def handle_signal(signum, frame):
            self.running = False
            
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
        
        while self.running:
            try:
                # Check and clear logs if needed
                LogCleaner.check_and_clear_logs()
                
                is_active, should_run_app = self.device_controller.check_remote_commands()
                
                if is_active is False:  # Khi server gửi is_active = False
                    logging.info("Shutdown command received")
                    self.shutdown_device()  # Thiết bị sẽ tắt
                    break
                
                logging.info(f"Status check - active: {is_active}, should_run: {should_run_app}")
                
                if is_active is False:
                    logging.info("Shutdown command received")
                    self.shutdown_device()
                    break
                    
                if should_run_app and not self.app_process:
                    logging.info("Starting app...")
                    self.start_app()
                elif not should_run_app and self.app_process:
                    logging.info("Stopping app...")
                    self.stop_app()
                
                # Check if app crashed
                if self.app_process and self.app_process.poll() is not None:
                    logging.warning("App crashed or closed unexpectedly")
                    self.app_process = None
                    self.device_controller.update_status(app_running=False)
                    
            except Exception as e:
                logging.error(f"Error in service controller: {e}")
                
            time.sleep(2)
            
        self.stop_app()

class DeviceController:
    def __init__(self):
        self.base_url = f"{BASE_URL}/api"  # Add /api prefix
        self.device_id = DEVICE_ID

    def update_status(self, is_active=None, app_running=None):
        try:
            url = f"{self.base_url}/devices/{self.device_id}/status/"  # Add /status/ suffix
            data = {
                "is_active": is_active,
                "app_running": app_running
            }
            response = requests.post(url, json=data, timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Failed to update status: {e}")
            return False

    def check_remote_commands(self):
        try:
            url = f"{self.base_url}/devices/{self.device_id}/status/"  # Add /status/ suffix
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("is_active", True), data.get("app_running", False)
        except requests.RequestException as e:
            logging.error(f"Failed to check remote commands: {e}")
            return True, False  # Default to keeping device on but app off
        except Exception as e:
            logging.error(f"Unexpected error in check_remote_commands: {e}")
            return True, False

if __name__ == "__main__":
    service = ServiceController()
    service.run()

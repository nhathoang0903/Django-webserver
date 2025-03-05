import os

# Server configuration
SERVER_IP = "192.168.5.38"
SERVER_PORT = "9000"
BASE_URL = f"http://{SERVER_IP}:{SERVER_PORT}"
HISTORY_API_URL = f"{BASE_URL}/history/"
CUSTOMER_HISTORY_LINK_URL = f"{BASE_URL}/api/customer-history-link/"  

# Device configuration
DEVICE_ID = "raspi_cart_001"
DEVICE_NAME = "Smart Cart Display 1"
DEVICE_TYPE = "raspberry_pi"

# Keyboard configuration
VIRTUAL_KEYBOARD_CMD = "matchbox-keyboard"
KEYBOARD_PATH = "/usr/bin/matchbox-keyboard"
KEYBOARD_ENV = {
    "DISPLAY": ":0",
    "XAUTHORITY": "/home/pi/.Xauthority"
}
KEYBOARD_CONFIG = "--xid"  

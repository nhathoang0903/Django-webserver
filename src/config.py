import os

# Server configuration
#SERVER_IP = "192.168.5.6"
#SERVER_PORT = "9000"
#BASE_URL = f"http://{SERVER_IP}:{SERVER_PORT}"
BASE_URL= f"http://192.168.5.75:9000/"
HISTORY_API_URL = f"{BASE_URL}/history/"
CUSTOMER_HISTORY_LINK_URL = f"{BASE_URL}/api/customer-history-link/"  

# Cart API configuration
CART_STATUS_API = f"{BASE_URL}/api/device/status/"
CART_END_SESSION_STATUS_API = f"{BASE_URL}/api/device/end-session/"
CART_END_SESSION_API = f"{BASE_URL}/api/device/end-session/"
CART_SHOPPING_MONITOR_API = f"{BASE_URL}/api/shopping/monitor/"
CART_CONNECT = f"{BASE_URL}/api/device/connect/"
CART_DISCONNECT = f"{BASE_URL}/api/device/disconnect/"
CART_CHECK_PAYMENT_SIGNAL = f"{BASE_URL}/api/shopping/payment-signal/"
CART_CANCEL_PAYMENT_SIGNAL = f"{BASE_URL}/api/shopping/cancel-payment-signal/"

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
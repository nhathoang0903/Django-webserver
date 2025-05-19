import requests
import socket
import logging
import netifaces
from requests.exceptions import RequestException
from config import BASE_URL, DEVICE_ID, CART_STATUS_API

class DeviceController:
    def __init__(self):
        self.BASE_URL = BASE_URL
        self.DEVICE_ID = DEVICE_ID
        self.STATUS_URL = CART_STATUS_API

    def get_device_ip(self):
        try:
            # Get all network interfaces
            interfaces = netifaces.interfaces()
            
            # Look for wlan0 or eth0 interfaces first
            preferred_interfaces = ['wlan0', 'eth0']
            for iface in preferred_interfaces:
                if iface in interfaces:
                    addrs = netifaces.ifaddresses(iface)
                    if netifaces.AF_INET in addrs:
                        ip_address = addrs[netifaces.AF_INET][0]['addr']
                        if not ip_address.startswith('127.'):
                            return ip_address

            # If preferred interfaces not found, try all interfaces
            for iface in interfaces:
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    ip_address = addrs[netifaces.AF_INET][0]['addr']
                    if not ip_address.startswith('127.'):
                        return ip_address
            
            logging.warning("Could not find non-localhost IP address")
            return "127.0.0.1"
        except Exception as e:
            logging.error(f"Failed to get IP address: {e}")
            return "127.0.0.1"

    def update_status(self, is_active=True, app_running=False):
        try:
            status_data = {
                "device_id": self.DEVICE_ID,
                "ip_address": self.get_device_ip(),
                "is_active": is_active,
                "app_running": app_running
            }
            response = requests.put(self.STATUS_URL, json=status_data, timeout=5)
            if response.status_code == 200:
                logging.info("Status updated successfully")
                return True
            else:
                logging.error(f"Failed to update status: {response.status_code}")
                return False
        except RequestException as e:
            logging.error(f"Network error updating status: {e}")
            return False

    def check_remote_commands(self):
        try:
            response = requests.get(f"{self.STATUS_URL}?device_id={self.DEVICE_ID}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("is_active"), data.get("app_running")
            else:
                logging.error(f"Failed to get status: {response.status_code}")
        except RequestException as e:
            logging.error(f"Network error checking status: {e}")
        return None, None

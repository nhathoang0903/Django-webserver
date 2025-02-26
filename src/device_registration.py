import requests
import socket
import json
import netifaces
from config import BASE_URL, DEVICE_ID, DEVICE_NAME, DEVICE_TYPE

def get_device_ip():
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
        
        return "127.0.0.1"
    except Exception as e:
        print(f"Failed to get IP address: {e}")
        return "127.0.0.1"

def register_device():
    API_URL = f"{BASE_URL}/devices/"
    
    # Prepare device data
    device_data = {
        "device_id": DEVICE_ID,
        "device_name": DEVICE_NAME,
        "device_type": DEVICE_TYPE,
        "ip_address": get_device_ip(),
        "is_active": True,
        "app_running": True
    }
    
    try:
        # Send POST request to register device
        response = requests.post(API_URL, json=device_data)
        
        if response.status_code == 200 or response.status_code == 201:
            print("Device registered successfully!")
            print("Response:", response.json())
        else:
            print(f"Failed to register device. Status code: {response.status_code}")
            print("Response:", response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Error registering device: {e}")

if __name__ == "__main__":
    register_device()

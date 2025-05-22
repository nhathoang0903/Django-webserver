from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeySequence
import sys
import os
import json
import requests
import logging
from config import DEVICE_ID, CART_END_SESSION_API

class BasePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_kiosk_mode()
        
    def setup_kiosk_mode(self):
        # Set window flags for kiosk mode
        self.setWindowFlags(
            Qt.Window | 
            Qt.FramelessWindowHint |  # No window decorations
            Qt.WindowStaysOnTopHint   # Always on top
        )
        
        # Set fixed size for 10.1-inch display
        self.setFixedSize(1920, 1080)
        
    def eventFilter(self, obj, event):
        # Handle Ctrl+X for emergency exit
        if event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            
            if modifiers & Qt.ControlModifier and key == Qt.Key_X:
                print("Emergency exit triggered")
                # Ensure clean session end before exit
                self.cleanup_session()
                sys.exit(0)
                
        return super().eventFilter(obj, event)
        
    def showEvent(self, event):
        # Ensure window is fullscreen when shown
        self.showFullScreen()
        super().showEvent(event)
        
    def closeEvent(self, event):
        # Make sure we clean up when any page is closed unexpectedly
        self.cleanup_session()
        super().closeEvent(event)
        
    def cleanup_session(self):
        """Clean up cart session when closing the application"""
        try:
            # Call the end session API with a short timeout
            response = requests.post(f"{CART_END_SESSION_API}{DEVICE_ID}/", timeout=1)
            print(f"Ending cart session: {response.status_code}")
        except Exception as e:
            print(f"Error ending cart session: {e}")
            
        # Try to clear phone number
        try:
            phone_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'config', 'phone_number.json')
            if os.path.exists(phone_path):
                with open(phone_path, 'w') as f:
                    json.dump({"phone_number": ""}, f)
        except Exception as e:
            print(f"Error clearing phone number: {e}")
            
        # Try to clear cart state
        try:
            from cart_state import CartState
            cart_state = CartState()
            cart_state.clear_cart()
        except Exception as e:
            print(f"Error clearing cart state: {e}")

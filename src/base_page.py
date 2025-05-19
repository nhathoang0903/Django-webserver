from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeySequence
import sys

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
                sys.exit(0)
                
        return super().eventFilter(obj, event)
        
    def showEvent(self, event):
        # Ensure window is fullscreen when shown
        self.showFullScreen()
        super().showEvent(event)

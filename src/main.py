import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QIcon
import os
from page1_welcome import WelcomePage
import subprocess

class KioskApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        
        # Set application-wide attributes
        self.setOverrideCursor(Qt.BlankCursor)  # Hide cursor
        
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
        # Show taskbar again on Raspberry Pi
        if os.path.exists('/usr/bin/lxpanel'):
            subprocess.Popen(['lxpanel', '--profile', 'LXDE-pi'])
            
def main():
    app = KioskApplication(sys.argv)
    
    # Show main window
    app.show_main_window()
    
    # Run application
    result = app.exec_()
    
    # Restore system state before exit
    app.restore_system_state()
    
    sys.exit(result)

if __name__ == '__main__':
    main()

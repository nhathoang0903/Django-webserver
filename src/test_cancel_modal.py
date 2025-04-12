import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsBlurEffect, QGraphicsOpacityEffect

from cancelshopping_modal import CancelShoppingModal

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cancel Shopping Modal Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Create layout
        layout = QVBoxLayout(self.central_widget)
        
        # Create button to show modal
        self.show_modal_button = QPushButton("Show Cancel Shopping Modal")
        self.show_modal_button.setFixedSize(300, 50)
        self.show_modal_button.clicked.connect(self.show_modal)
        layout.addWidget(self.show_modal_button, 0, Qt.AlignCenter)
        
        # Create blur effect and opacity effect for background
        self.blur_effect = QGraphicsBlurEffect()
        self.blur_effect.setBlurRadius(0)
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1)
        
        # Container for blur effect
        self.blur_container = QWidget()
        self.blur_container.setGraphicsEffect(self.blur_effect)
        
        # Modal instance
        self.modal = None
        
    def show_modal(self):
        # Apply blur and reduce opacity
        self.blur_effect.setBlurRadius(5)
        self.opacity_effect.setOpacity(0.7)
        self.central_widget.setGraphicsEffect(self.blur_effect)
        
        # Create and show modal
        self.modal = CancelShoppingModal(self)
        self.modal.cancelled.connect(self.handle_cancelled)
        self.modal.not_now.connect(self.handle_not_now)
        
        # Position modal in center of window
        x = (self.width() - self.modal.width()) // 2
        y = (self.height() - self.modal.height()) // 2
        self.modal.move(x, y)
        self.modal.show()
    
    def handle_cancelled(self):
        print("Shopping cancelled!")
        self.blur_effect.setBlurRadius(0)
        self.central_widget.setGraphicsEffect(None)
    
    def handle_not_now(self):
        print("Not now selected")
        self.blur_effect.setBlurRadius(0)
        self.central_widget.setGraphicsEffect(None)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_()) 
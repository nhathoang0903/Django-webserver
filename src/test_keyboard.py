from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QFont
# Sửa lại import path để match với cấu trúc thư mục
from dialogs.virtual_keyboard import VirtualKeyboard
import sys

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Test Virtual Keyboard')
        self.setGeometry(100, 100, 600, 500)  # Made taller to fit keyboard
        
        layout = QVBoxLayout()
        
        # Add input field
        self.input = QLineEdit()
        self.input.setFixedHeight(50)
        layout.addWidget(self.input)
        
        # Add keyboard
        self.keyboard = VirtualKeyboard(self)
        # Fix: Use key_pressed signal instead of text_input
        self.keyboard.key_pressed.connect(self.handleKeyPress)
        layout.addWidget(self.keyboard)
        
        self.setLayout(layout)
        
    def handleKeyPress(self, key):
        print(f"Key pressed: {key}")  # Debug print
        current = self.input.text()
        
        if key == 'backspace':
            self.input.setText(current[:-1])
        elif key == '\n':
            print("Enter pressed")
        else:
            self.input.setText(current + key)

def main():
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

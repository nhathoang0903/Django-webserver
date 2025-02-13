from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontDatabase
import os

class CancelShoppingModal(QFrame):
    cancelled = pyqtSignal()
    not_now = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(350, 250)  
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #000000;
            }
        """)

        self.init_ui()
    def load_fonts(self):
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 25)

        # Header with adjusted X button position
        header_container = QFrame()
        header_container.setFixedHeight(45)
        header_container.setStyleSheet("background-color: #F5F75C;")  
        header_container_layout = QHBoxLayout(header_container)
        header_container_layout.setContentsMargins(15, 0, 0, 0)  # Remove right margin

        title = QLabel("Are you sure you want to cancel?")
        title.setStyleSheet("""
            font-family: Inria Sans;
            font-size: 16px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)

        close_btn = QPushButton("X")
        close_btn.setFixedSize(45, 45)  # Make square
        close_btn.setStyleSheet("""
            QPushButton {
                font-family: Inria Sans;
                border-left: 1px solid #000000;
                color: #F50A0A;
                font-size: 20px;
                font-weight: bold;
                background: white;
                margin: 0px;
                padding: 0px;
            }
            QPushButton:hover {
                color: #666666;
            }
        """)
        close_btn.clicked.connect(self.handle_not_now)

        header_container_layout.addWidget(title)
        header_container_layout.addStretch()
        header_container_layout.addWidget(close_btn, 0, Qt.AlignRight)
        layout.addWidget(header_container)

        # Message container with proper margins
        message_container = QWidget()
        message_layout = QVBoxLayout(message_container)
        message_layout.setContentsMargins(20, 30, 20, 30)

        message = QLabel("Any items you have added to the cart will be\nremoved, and your current progress will be lost.")
        message.setStyleSheet("""
            font-family: Inria Sans;
            font-size: 13px;
            color: #000000;
            font-weight: bold;
            background: transparent;
            border: none;
            padding: 10px;
        """)
        message.setAlignment(Qt.AlignLeft)
        message_layout.addWidget(message)
        layout.addWidget(message_container)

        # Add spacing before buttons
        layout.addSpacing(20)

        # Buttons container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(20)

        not_now_btn = QPushButton("Not now")
        not_now_btn.setFixedSize(120, 35)
        not_now_btn.setStyleSheet("""
            QPushButton {
                background-color: #D9D9D9;
                border: none;
                border-radius: 14px;
                color: black;
                font-size: 12px;
                font-weight: bold;
            }
            # QPushButton:hover {
            #     background-color: #d0d0d0;
            # }
        """)
        not_now_btn.clicked.connect(self.handle_not_now)

        cancel_btn = QPushButton("Cancel payment")
        cancel_btn.setFixedSize(120, 35)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FB595C;
                border: none;
                border-radius: 14px;
                color: #000000;
                font-size: 12px;
                font-weight: bold;
            }
            # QPushButton:hover {
            #     background-color: #ff3333;
            # }
        """)
        cancel_btn.clicked.connect(self.handle_cancel)

        button_layout.addStretch()
        button_layout.addWidget(not_now_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        
        layout.addWidget(button_container)
        layout.addStretch(1)  # Giữ buttons ở vị trí thấp hơn

    def handle_not_now(self):
        if self.parent and hasattr(self.parent, 'blur_container'):
            self.parent.blur_effect.setBlurRadius(0)
            self.parent.opacity_effect.setOpacity(1)
        self.not_now.emit()
        self.hide()

    def handle_cancel(self):
        self.cancelled.emit()
        self.hide()
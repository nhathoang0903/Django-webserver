from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontDatabase, QFont
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

        # Header container with reduced width
        header_container = QFrame()
        header_container.setFixedHeight(45)
        header_container.setFixedWidth(308)  
        header_container.setStyleSheet("background-color: #F5F75C;")
        header_container_layout = QHBoxLayout(header_container)
        header_container_layout.setContentsMargins(15, 0, 0, 0)
        header_container_layout.setSpacing(0)

        # Fix title styling
        title = QLabel("Are you sure you want to cancel?")
        title.setFont(QFont("Inria Sans", 10, QFont.Bold))
        title.setStyleSheet("""
            QLabel {
                color: #000000;
                background: transparent;
                border: none;
            }
        """)

        # Update close button position and border
        close_btn = QPushButton("X")
        close_btn.setFixedSize(42, 45)
        close_btn.setFont(QFont("Inria Sans", 15, QFont.Bold))
        close_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #000000;
                border-right: none;  /* Remove right border */
                color: #F50A0A;
                background: white;
                margin: 0;
                padding: 0;
                text-align: center;
                line-height: 45px;
            }
            QPushButton:hover {
                color: #666666;
            }
        """)
        close_btn.clicked.connect(self.handle_not_now)

        # Create container for header and X button
        header_with_x = QWidget()
        header_with_x_layout = QHBoxLayout(header_with_x)
        header_with_x_layout.setContentsMargins(0, 0, 0, 0)
        header_with_x_layout.setSpacing(0)

        header_container_layout.addWidget(title)
        header_container_layout.addStretch()
        
        header_with_x_layout.addWidget(header_container)
        header_with_x_layout.addWidget(close_btn, 0, Qt.AlignRight | Qt.AlignTop)
        layout.addWidget(header_with_x)

        # Message container with increased height and no border
        message_container = QWidget()
        message_container.setFixedHeight(110)
        message_container.setStyleSheet("border: none; background: transparent;")
        message_layout = QVBoxLayout(message_container)
        message_layout.setContentsMargins(20, 15, 20, 15)  # Adjusted margins
        message_layout.setSpacing(10)  # Added some spacing

        # Update message font
        message = QLabel()
        message.setText("Any items you have added to the cart will be\nremoved, and your current progress will be lost.")
        message.setFont(QFont("Inria Sans", 7, QFont.Bold))
        # message.setWordWrap(True)  # Enable word wrap
        message.setStyleSheet("""
            QLabel {
                color: #000000;
                background: transparent;
                padding: 15px 10px 18px 10px;  
                qproperty-alignment: AlignLeft | AlignVCenter; 
                line-height: 1.5; 
                border: none;
            }
        """)
        
        # Enable font loaded before using in QLabel
        self.load_fonts() 
        
        message_layout.addWidget(message)
        layout.addWidget(message_container)

        # Add spacing before buttons
        layout.addSpacing(20)

        # Buttons container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(20)

        # Update button fonts
        not_now_btn = QPushButton("Not now")
        not_now_btn.setFixedSize(120, 35)
        not_now_btn.setFont(QFont("Inria Sans", 8, QFont.Bold))
        not_now_btn.setStyleSheet("""
            QPushButton {
                background-color: #D9D9D9;
                border: none;
                border-radius: 14px;
                color: black;
            }
        """)
        not_now_btn.clicked.connect(self.handle_not_now)

        cancel_btn = QPushButton("Cancel payment")
        cancel_btn.setFixedSize(120, 35)
        cancel_btn.setFont(QFont("Inria Sans", 8, QFont.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FB595C;
                border: none;
                border-radius: 14px;
                color: #000000;
            }
        """)
        cancel_btn.clicked.connect(self.handle_cancel)

        button_layout.addStretch()
        button_layout.addWidget(not_now_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        
        layout.addWidget(button_container)
        layout.addStretch(1)

    def handle_not_now(self):
        if self.parent and hasattr(self.parent, 'blur_container'):
            self.parent.blur_effect.setBlurRadius(0)
            self.parent.opacity_effect.setOpacity(1)
        self.not_now.emit()
        self.hide()

    def handle_cancel(self):
        # Emit signal only once and hide
        self.cancelled.emit()
        self.hide()
        # Don't handle cart clearing here - let page4 handle it
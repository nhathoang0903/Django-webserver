from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class CancelShoppingModal(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)  # Change this line
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 20px;
                border: 1px solid #CCCCCC;
            }
        """)
        
        self.init_ui()
        self.parent = parent  # Store parent reference
        self.home_page = None  # Add this line to store reference to home page

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header with text and X button
        header_layout = QHBoxLayout()
        title = QLabel("Are you sure you want to cancel?")
        title.setStyleSheet("font-family: Inter; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                font-size: 16px;
                font-weight: bold;
                color: #666666;
            }
            QPushButton:hover {
                color: #000000;
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn, alignment=Qt.AlignRight)
        layout.addLayout(header_layout)

        # Message
        message = QLabel("Any items you have added to the cart will be removed,\nand your current progress will be lost.")
        message.setStyleSheet("font-family: Inter; font-size: 14px; color: #666666;")
        message.setWordWrap(True)
        layout.addWidget(message)

        # Add stretch to push buttons to bottom
        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        not_now_btn = QPushButton("Not now")
        not_now_btn.setFixedSize(120, 40)
        not_now_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #507849;
                border-radius: 20px;
                color: #507849;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F0F6F1;
            }
        """)
        not_now_btn.clicked.connect(self.reject)
        
        cancel_btn = QPushButton("Cancel shopping")
        cancel_btn.setFixedSize(120, 40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 1px solid #D32F2F;
                border-radius: 20px;
                color: #D32F2F;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
                color: white;
            }
        """)
        cancel_btn.clicked.connect(self.go_home)  
        
        button_layout.addWidget(not_now_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def go_home(self):
        from page1_welcome import WelcomePage
        self.home_page = WelcomePage()  # Store as instance variable
        if self.parent:
            self.parent.home_page = self.home_page  # Also store in parent
            self.parent.close()  # Close shopping page
        self.home_page.show()
        self.accept()  # Close modal
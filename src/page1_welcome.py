from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                           QPushButton, QApplication, QMessageBox, QHBoxLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase
from page2_instruction import InstructionPage  
import os
from cart_state import CartState  # Add this import

class WelcomePage(QWidget):
    def __init__(self):
        super().__init__()
        # Clear any existing cart data when welcome page opens
        cart_state = CartState()
        cart_state.clear_cart()
        self.load_fonts()
        self.init_ui()

    def load_fonts(self):
        # Load custom fonts from font-family directory
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        
        # Load Tillana Bold
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        
        # Load Inria Sans Bold
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Bold.ttf'))
        
        # Load Poppins Italic
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        
        # Load Inter Bold
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))

    def init_ui(self):
        self.setWindowTitle('Smart Shopping Cart')
        self.setGeometry(100, 100, 800, 480)
        self.setFixedSize(800, 480)
        
        # Update stylesheet for full coverage
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F9F7;
            }
            QPushButton {
                background-color: #507849;
                color: white;
                border-radius: 24px;
                padding: 15px 10px;
                font-size: 14px;
                border: none;
                text-transform: uppercase;
                font-weight: bold;
                width: 145px;
                height: 18px;
            }
            QPushButton:hover {
                background-color: #3e5c38;
            }
        """)

        # Main layout
        layout = QHBoxLayout()
        layout.setContentsMargins(30, 8, 50, 50)  # Reduced top margin from 20 to 10
        layout.setSpacing(30)

        # Left side content
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # Changed to AlignTop
        left_layout.setSpacing(10)  # Reduced spacing from 15 to 10

        # Logo at the top left
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(154, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignLeft)
        left_layout.addWidget(logo_label)

        # Add some spacing
        left_layout.addSpacing(10)  

        # Welcome text using Inria Sans Bold
        welcome_label = QLabel("Welcome to Cartsy !")
        welcome_label.setFont(QFont("Inria Sans", 34, QFont.Bold))
        welcome_label.setStyleSheet("color: #3D6F4A;")
        left_layout.addWidget(welcome_label)

        # Tagline using Poppins Italic
        tagline_label = QLabel('"Shop smarter, enjoy life more"')
        tagline_label.setFont(QFont("Poppins", 15))
        tagline_label.setStyleSheet("""
            color: #E72225;
            font-style: italic;
        """)
        left_layout.addWidget(tagline_label)

        # Add less spacing before button
        left_layout.addSpacing(10)  # Reduced spacing from 15 to 10

        # Get Started button using Inter Bold
        start_button = QPushButton("GET STARTED")
        start_button.setFont(QFont("Inter", QFont.Bold))
        start_button.setCursor(Qt.PointingHandCursor)
        start_button.clicked.connect(self.start_shopping)
        left_layout.addWidget(start_button, alignment=Qt.AlignLeft)

        # Reduce stretch factor
        left_layout.addStretch(1) 

        # Right side image
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(50, 0, 0, 0)  # Increased left margin from 30 to 50
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # Keep VCenter alignment for instruction image
        
        welcome_img_label = QLabel()
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'welcome-instruction.png')
        img_pixmap = QPixmap(img_path)
        if not img_pixmap.isNull():
            welcome_img_label.setPixmap(img_pixmap.scaled(365, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        welcome_img_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter) # Keep VCenter alignment
        right_layout.addWidget(welcome_img_label)

        # Add containers to main layout
        layout.addWidget(left_container, 1)
        layout.addWidget(right_container, 1)

        self.setLayout(layout)

    def start_shopping(self):
        self.instruction_page = InstructionPage()
        self.instruction_page.show()
        print("Instruction page opened")
        self.hide()  # Hide the welcome page

if __name__ == '__main__':
    import sys
    
    app = QApplication(sys.argv)
    welcome = WelcomePage()
    welcome.show()

    sys.exit(app.exec_())
import json
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget, QDialog
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontDatabase, QFont
import os
from components.PageTransitionOverlay import PageTransitionOverlay
import requests
from config import CART_END_SESSION_API, DEVICE_ID
from utils.translation import _, get_current_language

class CancelShoppingModal(QFrame):
    cancelled = pyqtSignal()
    not_now = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(460, 310)  
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #000000;
            }
        """)

        self.init_ui()
        self.transition_overlay = PageTransitionOverlay(self)
        self.transition_in_progress = False  # Add this line

    def load_fonts(self):
        # Load and register fonts
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/static/Inter_24pt-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 30)

        # Header container with adjusted width
        header_container = QFrame()
        header_container.setFixedHeight(55)
        header_container.setFixedWidth(410)  # Reduced from 450 to 410 to match reduced modal width
        header_container.setStyleSheet("background-color: #F5F75C;")
        header_container_layout = QHBoxLayout(header_container)
        header_container_layout.setContentsMargins(20, 0, 0, 0)
        header_container_layout.setSpacing(0)

        # Fix title styling with larger font
        title = QLabel(_("cancelShoppingModal.title"))
        title.setFont(QFont("Inria Sans", 16, QFont.Bold))
        title.setStyleSheet("""
            QLabel {
                color: #000000;
                background: transparent;
                border: none;
            }
        """)

        # Update close button position and border
        close_btn = QPushButton("X")
        close_btn.setFixedSize(50, 55)
        close_btn.setFont(QFont("Inria Sans", 18, QFont.Bold))
        close_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #000000;
                border-right: none;  
                color: #F50A0A;
                background: white;
                margin: 0;
                padding: 0;
                text-align: center;
                line-height: 55px;
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
        message_container.setFixedHeight(100)
        message_container.setStyleSheet("border: none; background: transparent;")
        message_layout = QVBoxLayout(message_container)
        message_layout.setContentsMargins(25, 15, 25, 10)
        message_layout.setSpacing(12)

        # Update message font with larger size
        message = QLabel()
        message.setText(_("cancelShoppingModal.message"))
        message.setFont(QFont("Josefin Sans", 15))
        message.setWordWrap(True)
        message.setStyleSheet("""
            QLabel {
                color: #000000;
                background: transparent;
                padding: 18px 12px 20px 12px;  
                qproperty-alignment: AlignLeft | AlignVCenter; 
                line-height: 1.6; 
                border: none;
            }
        """)
        
        # Enable font loaded before using in QLabel
        self.load_fonts() 
        
        message_layout.addWidget(message)
        layout.addWidget(message_container)

        # Add spacing before buttons
        layout.addSpacing(13)

        # Buttons container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(35)

        # Update button fonts and sizes
        not_now_btn = QPushButton(_("cancelShoppingModal.notNow"))
        not_now_btn.setFixedSize(170, 50)
        not_now_btn.setFont(QFont("Inria Sans", 13, QFont.Bold))
        not_now_btn.setStyleSheet("""
            QPushButton {
                background-color: #CAF7B2;
                border: none;
                border-radius: 14px;
                color: black;
            }
        """)
        not_now_btn.clicked.connect(self.handle_not_now)

        cancel_btn = QPushButton(_("cancelShoppingModal.cancelPayment"))
        cancel_btn.setFixedSize(170, 50)
        cancel_btn.setFont(QFont("Inria Sans", 13, QFont.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #FB595C;
                border: none;
                border-radius: 14px;
                color: #000000;
            }
        """)
        cancel_btn.clicked.connect(self.handle_cancel_shopping)

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

    def handle_cancel_shopping(self):
        """Handle cancel payment button click with API call"""
        print("Cancel payment button clicked!")
        try:
            # Format API endpoint with device_id
            end_session_url = f"{CART_END_SESSION_API}{DEVICE_ID}/"
            print(f"Sending cancel request to: {end_session_url}")
            
            # Call API
            response = requests.post(end_session_url)
            print(f"API Response status code: {response.status_code}")
            print(f"API Response content: {response.text}")
            
            if response.status_code == 200:
                print("Successfully cancelled shopping session")
                # Clear phone number in JSON file
                try:
                    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        'config', 'phone_number.json')
                    with open(file_path, 'w') as f:
                        json.dump({"phone_number": ""}, f)
                    print("Successfully cleared phone number")
                except Exception as e:
                    print(f"Error clearing phone number: {e}")
            else:
                print(f"Error cancelling session: {response.text}")
                
        except Exception as e:
            print(f"Error calling end session API: {e}")
        
        # Emit signal to close modal and return to home
        self.cancelled.emit()
        self.hide()

    def handle_cancel(self):
        # Emit signal only once and hide
        if not self.transition_in_progress:  # Check if transition is already in progress
            self.transition_in_progress = True  # Set the flag to indicate transition is in progress
            self.cancelled.emit()
            self.hide()
        # Don't handle cart clearing here - let page4 handle it

    def accept(self):
        """Handle Yes button click"""
        def handle_transition():
            # Emit cancelled signal after overlay appears
            def emit_signal():
                if not self.transition_in_progress:  # Check if transition is already in progress
                    self.transition_in_progress = True  # Set the flag to indicate transition is in progress
                    self.cancelled.emit()
                    self.close()
                
            self.transition_overlay.fadeIn(emit_signal)
            
        handle_transition()

    def reject(self):
        """Handle No button click"""
        self.not_now.emit()
        self.close()
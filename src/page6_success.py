from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                           QApplication, QHBoxLayout)
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QFont, QPixmap, QIcon, QFontDatabase
from PyQt5.QtMultimedia import QSoundEffect  # Replace QSound with QSoundEffect
import os
import json
import random
import datetime
import requests
from cart_state import CartState
from page_timing import PageTiming
from components.PageTransitionOverlay import PageTransitionOverlay  
from base_page import BasePage  
from config import HISTORY_API_URL, CUSTOMER_HISTORY_LINK_URL, DEVICE_ID

class SuccessPage(BasePage):  # Changed from QWidget to BasePage
    def __init__(self):
        super().__init__()  # Call BasePage init
        self.installEventFilter(self)  # Register event filter
        self.cart_state = CartState()
        self.load_fonts()
        self.init_ui()
        # Set application icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))
        # Send data to API
        self.send_to_history_api()
        # Clear cart only once at initialization
        self.cart_state.clear_cart()
        # Initialize transition overlay
        self.transition_overlay = PageTransitionOverlay(self)

    def load_fonts(self):
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))

    def send_to_history_api(self):
        """Return True if data was sent successfully"""
        try:
            # Read shopping process data
            with open(CartState.JSON_PATH, 'r') as f:
                shopping_data = json.load(f)

            # Prepare product list
            product_list = []
            for product in shopping_data["detected_products"]:
                product_list.append({
                    "name": product["product_name"],
                    "quantity": product["quantity"],
                    "price": product["price"] / product["quantity"]  # Price per unit
                })

            # Prepare payload
            payload = {
                "purchase_id": random.randint(1, 100),
                "random_id": str(random.randint(10000, 99999)),
                "timestamp": datetime.datetime.now().isoformat(),
                "total_amount": str(shopping_data["total_bill"]),
                "product": json.dumps(product_list)
            }

            # Send POST request using config URL
            response = requests.post(
                HISTORY_API_URL,
                json=payload
            )

            if response.status_code == 201:
                response_data = response.json()
                
                # Get the current mode from cart state
                cart_mode = ""
                try:
                    with open(CartState.JSON_PATH, 'r') as f:
                        cart_data = json.load(f)
                        cart_mode = cart_data.get("mode", "")
                except Exception as e:
                    print(f"Error reading cart mode: {e}")

                # Only include phone number if not in guest mode
                phone_number = ""
                if cart_mode != "guest":
                    try:
                        phone_number_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                                       'config', 'phone_number.json')
                        with open(phone_number_path, 'r') as f:
                            phone_data = json.load(f)
                            phone_number = phone_data.get("phone_number", "")
                    except Exception as e:
                        print(f"Error reading phone number: {e}")

                # Send customer history link data based on mode
                customer_data = {
                    "random_id": response_data["random_id"],
                    "username": phone_number,  # Will be empty for guest mode
                    "device_id": DEVICE_ID
                }
                
                print(f"Sending customer data: {customer_data}")
                customer_response = requests.post(
                    CUSTOMER_HISTORY_LINK_URL,
                    json=customer_data
                )
                
                if customer_response.status_code == 201:
                    print("Successfully sent customer history link")
                    
                    # Clear phone number after successful API calls
                    try:
                        phone_number_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                                        'config', 'phone_number.json')
                        if os.path.exists(phone_number_path):
                            with open(phone_number_path, 'w') as f:
                                json.dump({"phone_number": ""}, f)
                            print("Phone number cleared successfully")
                    except Exception as e:
                        print(f"Error clearing phone number: {e}")
                        
                    return True
                    
            return False

        except Exception as e:
            print(f"Error sending data to history API: {e}")
            return False

    def init_ui(self):
        self.setWindowTitle('Payment Success')
        # Remove setGeometry and setFixedSize since handled by BasePage

        self.setStyleSheet("background-color: #F0F6F1;")

        # Remove redundant sound-playing logic

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))

        # Main layout với style giống page5
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Logo section with left alignment
        logo_section = QWidget()
        logo_layout = QVBoxLayout(logo_section)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(0)

        # Logo 
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
        logo_pixmap = QPixmap(logo_path)
        logo_label.setPixmap(logo_pixmap.scaled(154, 64, Qt.KeepAspectRatio))
        logo_layout.addWidget(logo_label, alignment=Qt.AlignLeft)
        main_layout.addWidget(logo_section)

        # Center content với margin top nhỏ hơn
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.setContentsMargins(0, -20, 0, 0)  # Negative top margin to move content up
        center_layout.setSpacing(10)  # Reduced spacing between elements
        
        # Success image
        success_label = QLabel()
        success_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'paymentsuccess.png')
        success_pixmap = QPixmap(success_path)
        
        if success_pixmap.isNull():
            # print(f"Error: Could not load image from {success_path}")
            # Tạo một placeholder label nếu không load được hình
            success_label.setText("Payment Success!")
            success_label.setStyleSheet("font-size: 30px; color: #2BA616;")
        else:
            print(f"Successfully loaded image from {success_path}")
            success_label.setPixmap(success_pixmap.scaled(137, 117, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
        success_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(success_label)

        # Text sections with reduced spacing
        thank_label = QLabel("Thank you!")
        thank_label.setFont(QFont("Inria Sans", 30, QFont.Bold))
        thank_label.setStyleSheet("color: #2BA616;")
        thank_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(thank_label)

        success_msg = QLabel("Payment done successfully")
        success_msg.setFont(QFont("Inria Sans", 20))
        success_msg.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(success_msg)

        redirect_msg = QLabel("You will be redirected to the homepage shortly\nor click here to return to the home page")
        redirect_msg.setFont(QFont("Inria Sans", 10))
        redirect_msg.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(redirect_msg)

        # Add stretch before button to push it down
        center_layout.addStretch()

        # Home button với style giống button SCAN page3
        home_btn = QPushButton("HOME")
        home_btn.setFixedSize(154, 42)  # Kích thước giống button SCAN
        home_btn.setFont(QFont("Inter", 14, QFont.Bold))
        home_btn.setStyleSheet("""
            QPushButton {
                background-color: #4E8F5F;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 20px;
                text-transform: uppercase;
            }
            QPushButton:hover {
                background-color: #154D34;
            }
            QPushButton:pressed {
                background-color: #0F3B28;
            }
        """)
        home_btn.clicked.connect(self.go_home)
        center_layout.addWidget(home_btn, alignment=Qt.AlignCenter)

        main_layout.addWidget(center_widget)

        # Initialize timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)  # Timer will only fire once
        self.timer.timeout.connect(self.go_home)
        self.timer.start(5000)  # 5 seconds

    def go_home(self):
        """Clear data and return to the home page."""
        if hasattr(self, 'timer'):
            self.timer.stop()  # Stop the timer

        # Clear cart data only
        self.cart_state.clear_cart()  # Clear cart state
        try:
            # Remove cart data file if it exists
            if os.path.exists(CartState.JSON_PATH):
                os.remove(CartState.JSON_PATH)
                print("Cart data file removed successfully")
        except Exception as e:
            print(f"Error clearing cart data: {e}")

        # Transition to WelcomePage only after clearing data
        def transition_to_home():
            start_time = PageTiming.start_timing()
            from page1_welcome import WelcomePage
            self.home_page = WelcomePage()

            def show_new_page():
                self.home_page.show()
                self.transition_overlay.fadeOut(lambda: self.close())
                PageTiming.end_timing(start_time, "SuccessPage", "WelcomePage")

            self.transition_overlay.fadeIn(show_new_page)

        # Ensure data is cleared before transitioning
        QTimer.singleShot(100, transition_to_home)

    def closeEvent(self, event):
        if hasattr(self, 'timer'):
            self.timer.stop()  # Ensure timer is stopped when window closes
        super().closeEvent(event)

if __name__ == '__main__': 
    import sys
    app = QApplication(sys.argv)
    window = SuccessPage()
    window.show()
    sys.exit(app.exec_())
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
from utils.translation import _, get_current_language  

class SuccessPage(BasePage):  # Changed from QWidget to BasePage
    # Add a class variable to track if history has been posted
    _history_posted = False
    
    def __init__(self):
        super().__init__()  # Call BasePage init
        self.installEventFilter(self)  # Register event filter
        self.cart_state = CartState()
        self.load_fonts()
        self.init_ui()
        # Set application icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))
        # Gửi dữ liệu API trước, sau đó xóa số điện thoại nếu cần
        if not SuccessPage._history_posted:
            if self.send_to_history_api():
                SuccessPage._history_posted = True
                self.clear_phone_number()
        # Clear cart only once at initialization
        self.cart_state.clear_cart()
        # Initialize transition overlay
        self.transition_overlay = PageTransitionOverlay(self)
        
        # Initialize timer but don't start it yet
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)  # Timer will only fire once
        self.timer.timeout.connect(self.go_home)

    def load_fonts(self):
        # Load necessary fonts
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/static/Inter_24pt-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))
    

    def clear_phone_number(self):
        """Clear phone number from config file"""
        try:
            phone_number_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        'config', 'phone_number.json')
            if os.path.exists(phone_number_path):
                with open(phone_number_path, 'w') as f:
                    json.dump({"phone_number": ""}, f, indent=4)
                print("Phone number cleared successfully")
                return True
        except Exception as e:
            print(f"Error clearing phone number: {e}")
            return False
        

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

            # Import the donation amount from QRCodePage
            from page5_qrcode import QRCodePage
            
            # Prepare payload with donation amount
            payload = {
                "purchase_id": random.randint(1, 100),
                "random_id": str(random.randint(10000, 99999)),
                "timestamp": datetime.datetime.now().isoformat(),
                "total_amount": str(QRCodePage.donation_amount),  # Use the donation amount
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

                # Determine phone number or set to "unknown member" for guest mode
                phone_number = "unknown member" if cart_mode == "guest" else ""
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
                    "device_id": DEVICE_ID,
                    "note": QRCodePage.transfer_content if hasattr(QRCodePage, 'transfer_content') else ""
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
        self.setWindowTitle(_('successPage.title'))
        # Remove setGeometry and setFixedSize since handled by BasePage

        self.setStyleSheet("background-color: #F0F6F1;")

        # Remove redundant sound-playing logic

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))

        # Main layout with adjusted margins to prevent cutting off
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(80, 10, 80, 20)  # Reduced top and bottom margins

        # Logo section with much larger size to match page1
        logo_section = QWidget()
        logo_layout = QHBoxLayout(logo_section)  # Changed to HBoxLayout like page1
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(40)  # Match spacing from page1

        # Logo with much larger size to match page1
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(400, 166, Qt.KeepAspectRatio, Qt.SmoothTransformation))  # Slightly reduced to prevent cut-off
        logo_label.setAlignment(Qt.AlignLeft)
        logo_layout.addWidget(logo_label)
        
        # Add stretch to push logo to left like page1
        logo_layout.addStretch()
        
        # Add logo section to main layout
        main_layout.addWidget(logo_section)

        # Center content with adjusted spacing
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.setContentsMargins(0, 10, 0, 0)  # Reduced top margin to prevent cut-off
        center_layout.setSpacing(30)  # Slightly reduced spacing to fit everything
        
        # Success image with adjusted size
        success_label = QLabel()
        success_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'paymentsuccess.png')
        success_pixmap = QPixmap(success_path)
        
        if success_pixmap.isNull():
            success_label.setText(_("successPage.placeholder"))
            success_label.setStyleSheet("font-size: 50px; color: #2BA616;")  # Slightly reduced font size
        else:
            print(f"Successfully loaded image from {success_path}")
            success_label.setPixmap(success_pixmap.scaled(250, 213, Qt.KeepAspectRatio, Qt.SmoothTransformation))  # Slightly reduced size
            
        success_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(success_label)

        # Text sections with adjusted fonts
        thank_label = QLabel(_("successPage.thankYou"))
        thank_label.setFont(QFont("Inria Sans", 54, QFont.Bold))  # Slightly reduced font size
        thank_label.setStyleSheet("color: #2BA616;")
        thank_label.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(thank_label)

        success_msg = QLabel(_("successPage.paymentSuccess"))
        success_msg.setFont(QFont("Inria Sans", 40))  # Slightly reduced font size
        success_msg.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(success_msg)

        redirect_msg = QLabel(_("successPage.redirectMessage"))
        redirect_msg.setFont(QFont("Inria Sans", 24))  # Slightly reduced font size
        redirect_msg.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(redirect_msg)

        # Reduced stretch to allow more room for content
        center_layout.addStretch(1)

        # Home button with adjusted size
        home_btn = QPushButton(_("successPage.homeButton"))
        home_btn.setFixedSize(350, 90)  # Slightly reduced button size
        home_btn.setFont(QFont("Inter", 28, QFont.Bold))  # Slightly reduced font size
        home_btn.setStyleSheet("""
            QPushButton {
                background-color: #4E8F5F;
                color: white;
                border: none;
                border-radius: 30px;
                padding: 10px 25px;
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

        # Reduced bottom spacing
        center_layout.addSpacing(20)

        # Add center widget to main layout with stretch
        main_layout.addWidget(center_widget, 1)

        # No longer initializing timer here - moved to showEvent

    def showEvent(self, event):
        # Start the timer when the page is actually shown
        self.timer.start(5000)  # 5 seconds
        super().showEvent(event)

    def go_home(self):
        """Clear data and return to the home page."""
        if hasattr(self, 'timer'):
            self.timer.stop()  # Stop the timer

        # Clear phone number and cart data
        self.clear_phone_number()
        self.cart_state.clear_cart()

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
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Force CPU
import torch
torch.set_default_dtype(torch.float32)  # Thay thế set_default_tensor_type
torch.set_default_device("cpu")        # Thiết lập thiết bị mặc định
torch.set_num_threads(1)  # Set number of threads
import warnings
warnings.filterwarnings("ignore")
import gc
import logging 
import subprocess

from base_page import BasePage 
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                           QFrame, QApplication, QPushButton) 
from mbbank import MBBank 
from PyQt5.QtCore import Qt, QTimer, QDateTime, pyqtSignal, QUrl
from PyQt5.QtGui import QFont, QPixmap, QIcon, QImage, QColor, QBitmap, QFontDatabase, QFontMetrics
from PyQt5.QtMultimedia import QSoundEffect  # Ensure QSoundEffect is used
import os
import requests
import cv2
import numpy as np
import io
from io import BytesIO
from datetime import datetime, timedelta
import time
import json
from PIL import Image, ImageDraw
from cart_state import CartState
from threading import Thread, Event  
from page_timing import PageTiming
from components.PageTransitionOverlay import PageTransitionOverlay
import pyttsx3
import qrcode
from vietqr.VietQR import genQRString, getBincode
from config import CART_CANCEL_PAYMENT_SIGNAL, DEVICE_ID
from utils.translation import _, get_current_language  # Add translation import if not already there

class QRCodePage(BasePage):  # Changed from QWidget to BasePage
    switch_to_success = pyqtSignal()  # Signal for page switching
    payment_completed = pyqtSignal(bool)  # Signal for payment status
    donation_amount = 0  # Variable to store the donation amount
    transfer_content = ""  # Variable to store transfer content
    
    def __init__(self):
        # Ghi lại thời gian bắt đầu khởi tạo
        init_start_time = time.time()
        print(f"[QR_TIMING] Starting QRCodePage initialization at: {init_start_time}")
        
        # Force CPU configuration before any other initialization
        self.configure_device()
        print(f"[QR_TIMING] Device configured at: {time.time() - init_start_time:.4f}s")
        
        super().__init__()
        print(f"[QR_TIMING] BasePage initialized at: {time.time() - init_start_time:.4f}s")
        
        # Define common size for QR code and charity image - moved to class level
        self.common_size = 250  # Reduced size for better display
        
        # Disable sound functionality (lightweight)
        self.sound_enabled = False
        
        # Flag to prevent multiple button clicks
        self.processing_action = False
        
        # Register event filter
        self.installEventFilter(self)
        self.page_load_time = time.time()
        
        # Simplify initialization:
        # 1. Set minimum attributes first
        self.transition_overlay = PageTransitionOverlay(self)
        self.setWindowTitle('Charity Donation')
        self.setStyleSheet("background-color: #F5F9F7;")
        
        # Set window icon (defer image loading)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))
        
        # Core data loading
        print(f"[QR_TIMING] Starting to load cart state at: {time.time() - init_start_time:.4f}s")
        self.cart_state = CartState()
        
        # Calculate total first - do this only once
        print(f"[QR_TIMING] Calculating total amount at: {time.time() - init_start_time:.4f}s")
        raw_total = sum(float(product['price']) * quantity 
                      for product, quantity in self.cart_state.cart_items)
        self.total_amount = int(raw_total)
        print(f"[QR_TIMING] Initialized total amount: {self.total_amount} at {time.time() - init_start_time:.4f}s")
        
        # Quick validation - allow zero for charity
        # if self.total_amount == 0:
        #     from PyQt5.QtWidgets import QMessageBox
        #     msg = QMessageBox()
        #     msg.setIcon(QMessageBox.Warning)
        #     msg.setText("Invalid total amount")
        #     msg.setInformativeText("Cannot generate QR code for zero amount.")
        #     msg.setWindowTitle("Error")
        #     msg.exec_()
        #     self.close()
        #     return
        
        # Setup core timing variables
        self.qr_start_time = None
        self.processed_transaction_ids = set()
        
        # Initialize UI early
        print(f"[QR_TIMING] Starting UI initialization at: {time.time() - init_start_time:.4f}s")
        self.load_fonts()
        self.init_ui()
        print(f"[QR_TIMING] UI initialized at: {time.time() - init_start_time:.4f}s")
        
        # Setup timers and connect signals
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_seconds = 60  # Reduced to 1 minute
        self.target_time = datetime.now()
        
        # Connect signals - đã khai báo ở mức lớp, chỉ connect ở đây
        self.switch_to_success.connect(self.handle_success)
        self.shopping_page = None
        
        # Load QR code (heavy operation) - show loading first, then generate in QTimer
        self.qr_label.setText(_("qrCodePage.loading"))
        
        # Generate QR code with a short delay to allow UI to show first
        QTimer.singleShot(50, self.load_qr_code)
        
        self.stop_transaction_check = Event()
        print(f"[QR_TIMING] QRCodePage initialization completed at: {time.time() - init_start_time:.4f}s")

    def configure_device(self):
        """Configure CUDA and torch settings"""
        # Force CPU
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # Force CPU tensors
        torch.set_default_dtype(torch.float32)  # Thay thế set_default_tensor_type
        torch.set_default_device("cpu")        # Thiết lập thiết bị mặc định
        torch.set_num_threads(1)
        
        # Move any existing CUDA tensors to CPU
        if hasattr(torch, 'cuda') and torch.cuda.is_available():
            torch.cuda.empty_cache()
            for obj in gc.get_objects():
                try:
                    if torch.is_tensor(obj):
                        obj = obj.cpu()
                except:
                    pass

    def load_fonts(self):
        # Register various fonts
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/static/Inter_24pt-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Bold.ttf'))

    def init_ui(self):
        self.setWindowTitle('Charity Donation')
        self.setStyleSheet("background-color: #F5F9F7;")

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))

        # Use class-level common_size variable
        # Define common button size
        button_width = 200
        button_height = 60  # Increased from 50

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Left Section - Will now contain QR code and information
        left_section = QWidget()
        left_layout = QVBoxLayout(left_section)
        # Reduce all margins to minimize lost space
        left_layout.setContentsMargins(10, 0, 10, 5)
        left_layout.setSpacing(0)  # Set minimal spacing to control precisely

        # QR Code Container - create a separate container with custom size
        qr_container = QWidget()
        # Set fixed height to ensure it doesn't get compressed
        qr_container.setFixedHeight(self.common_size)
        qr_container_layout = QVBoxLayout(qr_container)
        qr_container_layout.setContentsMargins(0, 0, 0, 0)
        qr_container_layout.setSpacing(0)
        qr_container_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # QR Code Frame with adjusted size
        self.qr_frame = QFrame()
        self.qr_frame.setFixedSize(self.common_size, self.common_size)  # Use common size
        self.qr_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F9F7;
                border: none;
            }
        """)
        
        # QR Code Label
        self.qr_label = QLabel(self.qr_frame)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setFixedSize(self.common_size, self.common_size)  # Use common size
        self.qr_label.setText(_("qrCodePage.loading"))
        self.qr_label.setStyleSheet("background-color: transparent;")
        
        # Add QR code to container with top alignment
        qr_container_layout.addWidget(self.qr_frame, 0, Qt.AlignTop | Qt.AlignHCenter)
        
        # QR container to main layout with top margin
        left_layout.addSpacing(20)  # Add space at the top
        left_layout.addWidget(qr_container, 0, Qt.AlignTop | Qt.AlignHCenter)
        
        # Add flexible stretch to push everything else to the bottom
        left_layout.addStretch(2)

        # Bottom container for all info and buttons
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)  # Small space between elements
        
        # Payment Details Container - smaller and compact
        details_frame = QFrame()
        details_frame.setStyleSheet("""
            background-color: transparent;
        """)
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(0, 0, 0, 0)  # Remove internal margins
        details_layout.setSpacing(2)  # Slightly increased spacing between detail items

        # Amount with slightly increased font
        self.amount_label = QLabel()
        self.amount_label.setFont(QFont("Inria Sans", 10, QFont.Bold))  # Use QFont.Bold
        amount_text = sum(float(product['price']) * quantity 
                         for product, quantity in self.cart_state.cart_items)
        self.amount_label.setText(f"{_('qrCodePage.amount')}{'{:,.0f}'.format(amount_text).replace(',', '.')} vnđ")

        # Account number - new information
        account_number = "0375712517"
        account_label = QLabel(f"{_('qrCodePage.accountNumber')}{account_number}")
        account_label.setFont(QFont("Inria Sans", 10, QFont.Bold))  # Use QFont.Bold
        
        # Account Details - increased font
        acc_name_label = QLabel(_("qrCodePage.accountName"))
        acc_name_label.setFont(QFont("Inria Sans", 10))  # Increased font size
        
        bank_label = QLabel(_("qrCodePage.bankName"))
        bank_label.setFont(QFont("Inria Sans", 10))  # Increased font size

        # Add all labels to details layout
        for label in [self.amount_label, account_label, acc_name_label, bank_label]:
            label.setAlignment(Qt.AlignCenter)
            details_layout.addWidget(label)
  
        # Add details frame to bottom layout
        bottom_layout.addWidget(details_frame, alignment=Qt.AlignCenter)
        
        # Zero spacing between info and time
        bottom_layout.addSpacing(0)
        
        # Countdown and generation time
        time_container = QWidget()
        time_layout = QVBoxLayout(time_container)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(1)  # Minimal spacing
        
        # Countdown label
        self.countdown_label = QLabel()
        self.countdown_label.setFont(QFont("Inria Sans", 10, QFont.Bold))  # Use QFont.Bold
        self.countdown_label.setStyleSheet("color: #D30E11;")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.hide()

        # Generation time label
        self.gen_time_label = QLabel()
        italic_font = QFont("Inria Sans", 10)
        italic_font.setItalic(True)  # Proper way to set italic
        self.gen_time_label.setFont(italic_font)
        self.gen_time_label.setAlignment(Qt.AlignCenter)
        self.gen_time_label.hide()
        
        # Add labels to time container
        time_layout.addWidget(self.countdown_label, alignment=Qt.AlignCenter)
        time_layout.addWidget(self.gen_time_label, alignment=Qt.AlignCenter)
        
        # Add time container to bottom layout
        bottom_layout.addWidget(time_container, alignment=Qt.AlignCenter)
        
        # Add buttons to bottom layout
        # Cancel Payment button - use common button size
        self.cancel_button = QPushButton(_("qrCodePage.cancelPayment"))
        self.cancel_button.setFont(QFont("Josefin Sans", 15, QFont.Bold))  # Use QFont.Bold
        self.cancel_button.setFixedSize(button_width, button_height)  # Use common button size
        self.cancel_button.setStyleSheet("""
            background-color: #416FFA;
            color: white;
            border-radius:15px;
        """)
        self.cancel_button.clicked.connect(self.cancel_payment)
        bottom_layout.addWidget(self.cancel_button, alignment=Qt.AlignCenter)
        
        # Add the bottom container to main layout
        left_layout.addWidget(bottom_container, 0, Qt.AlignBottom)

        # Add left section to main layout
        main_layout.addWidget(left_section)

        # Right Section - Will now contain charity image and message
        right_section = QWidget()
        right_layout = QVBoxLayout(right_section)
        right_layout.setContentsMargins(10, 0, 10, 5)  # Match left section margins
        right_layout.setSpacing(0)  # Match left section spacing
        right_layout.setAlignment(Qt.AlignTop)
        
        # Charity image container - match QR code container
        charity_container = QWidget()
        charity_container.setFixedHeight(self.common_size)  # Match QR container height
        charity_layout = QVBoxLayout(charity_container)
        charity_layout.setContentsMargins(0, 0, 0, 0)
        charity_layout.setSpacing(0)
        charity_layout.setAlignment(Qt.AlignCenter)

        # Charity image
        charity_label = QLabel()
        charity_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'lovecharity.png')
        charity_pixmap = QPixmap(charity_path)
        
        if not charity_pixmap.isNull():
            charity_label.setPixmap(charity_pixmap.scaled(self.common_size, self.common_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            charity_label.setText("Charity Image")
            charity_label.setStyleSheet("font-size: 24px; color: #507849;")
            
        charity_label.setAlignment(Qt.AlignCenter)
        charity_label.setFixedSize(self.common_size, self.common_size)  # Match QR code size
        charity_layout.addWidget(charity_label, alignment=Qt.AlignCenter)
        
        # Add charity container to right layout with top margin
        right_layout.addSpacing(20)  # Add space at the top
        right_layout.addWidget(charity_container, alignment=Qt.AlignCenter | Qt.AlignTop)
        
        # Message container moved below charity image
        message_container = QWidget()
        message_container.setFixedWidth(self.common_size)  # Match common size
        message_layout = QVBoxLayout(message_container)
        message_layout.setContentsMargins(0, 10, 0, 0)  # Add top margin
        
        # Charity message with larger font size
        message_label = QLabel(_("qrCodePage.charityMessage"))
        message_font = QFont("Josefin Sans", 15)
        message_font.setItalic(True)  # Proper way to set italic
        message_label.setFont(message_font)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setWordWrap(True) 
        message_label.setStyleSheet("""
            color: #D30E11; 
            margin: 0px; 
            padding: 0px;
        """)
        
        message_layout.addWidget(message_label, alignment=Qt.AlignCenter)
        right_layout.addWidget(message_container, alignment=Qt.AlignCenter)
        
        # Add stretch to push button to bottom
        right_layout.addStretch(2) 
        
        # No Banking button 
        self.no_banking_button = QPushButton(_("qrCodePage.heartfeltSupport"))
        self.no_banking_button.setFont(QFont("Josefin Sans", 15, QFont.Bold)) 
        self.no_banking_button.setFixedSize(button_width, button_height) 
        self.no_banking_button.setStyleSheet("""
            background-color: #CC95BA;
            color: white;
            border-radius:15px;
        """)
        self.no_banking_button.clicked.connect(self.no_banking)
        right_layout.addWidget(self.no_banking_button, alignment=Qt.AlignCenter)
        
        # Add right section to main layout
        main_layout.addWidget(right_section)

    def load_qr_code(self):
        """Optimized QR code generation"""
        qr_start = time.time()
        print(f"[QR_TIMING] Starting QR code generation at: {qr_start}")
        
        try:
            # Set the start time when QR is generated
            self.qr_start_time = datetime.now()
            
            # Generate QR directly in main thread to fix UI update issues
            try:
                # VietQR configuration
                bank_name = "MB"  # MB Bank
                account_number = "0375712517"  #account number 
                bank_code = getBincode(bank_name)
                print(f"[QR_TIMING] Got bank code at: {time.time() - qr_start:.4f}s")

                # Generate VietQR string with proper format
                vietqr_string = genQRString(
                    merchant_id=account_number,
                    acq=bank_code,
                    # amount=str(self.total_amount), 
                    merchant_name="NGUYEN THE NGO",
                    service_code="QRIBFTTA",  
                    currency="704",            # VND currency code
                    country_code="VN",         # Vietnam country code
                    merchant_city="HO CHI MINH",
                    merchant_category="5499",  # 5499 is for Misc Food Stores
                    bill_number="SC" + datetime.now().strftime("%Y%m%d%H%M%S")  # Generate a unique bill number
                )
                print(f"[QR_TIMING] Generated VietQR string at: {time.time() - qr_start:.4f}s")
                
                # Create QR code with custom styling
                qr = qrcode.QRCode(
                    version=6,  # Increased version for better compatibility
                    error_correction=qrcode.constants.ERROR_CORRECT_H,
                    box_size=10,  # Reduced box size for better fit
                    border=4
                )
                
                qr.add_data(vietqr_string)
                qr.make(fit=True)
                print(f"[QR_TIMING] QR code created at: {time.time() - qr_start:.4f}s")
                
                # Create QR image with custom colors matching button color #507849
                qr_img = qr.make_image(fill_color="#507849", back_color="#F5F9F7").convert("RGBA")
                print(f"[QR_TIMING] QR image generated at: {time.time() - qr_start:.4f}s")
                
                # Convert PIL Image to QPixmap using BytesIO
                img_byte_array = io.BytesIO()
                qr_img.save(img_byte_array, format='PNG')
                img_byte_array.seek(0)
                print(f"[QR_TIMING] Converted to bytes at: {time.time() - qr_start:.4f}s")
                
                # Create QPixmap from bytes and update UI directly
                qr_pixmap = QPixmap()
                qr_pixmap.loadFromData(img_byte_array.getvalue())
                
                # Update UI with properly scaled QR code - match to common_size
                print(f"[QR_TIMING] About to update UI at: {time.time() - qr_start:.4f}s")
                self.qr_label.setPixmap(qr_pixmap.scaled(self.common_size, self.common_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.qr_label.setAlignment(Qt.AlignCenter)
                print(f"[QR_TIMING] QR image displayed at: {time.time() - qr_start:.4f}s")
                
                # Update date/time display
                current_time = QDateTime.currentDateTime()
                time_str = current_time.toString('hh:mm:ss')
                month_str = current_time.toString('MMM')
                day = current_time.date().day()
                year_str = current_time.toString('yyyy')
                
                # Get ordinal suffix
                if day in [1, 21, 31]:
                    suffix = "st"
                elif day in [2, 22]:
                    suffix = "nd"
                elif day in [3, 23]:
                    suffix = "rd"
                else:
                    suffix = "th"
                
                date_str = f"{day}<sup>{suffix}</sup>"
                self.gen_time_label.setText(
                    f"{_('qrCodePage.generated')}{time_str}, {month_str} {date_str}, {year_str}")
                self.gen_time_label.setTextFormat(Qt.RichText)
                self.gen_time_label.show()
                print(f"[QR_TIMING] Generation time displayed at: {time.time() - qr_start:.4f}s")
                
                # Đảm bảo UI được cập nhật ngay lập tức
                QApplication.processEvents()
                
                # Start countdown
                self.countdown_timer.start(1000)
                self.countdown_label.show()
                print(f"[QR_TIMING] Countdown started at: {time.time() - qr_start:.4f}s")
                
                # Start transaction check after UI được cập nhật
                self.start_transaction_check()
                print(f"[QR_TIMING] Transaction check started at: {time.time() - qr_start:.4f}s")
                print(f"[QR_TIMING] Total QR code generation time: {time.time() - qr_start:.4f}s")
                
            except Exception as e:
                print(f"Error in QR generation: {e}")
                self.qr_label.setText(f"Error: {str(e)}")
                # Ensure UI update is processed
                QApplication.processEvents()
                
                # Show transition overlay before returning to shopping
                if not hasattr(self, 'transition_in_progress') or not self.transition_in_progress:
                    self.transition_in_progress = True
                    self.transition_overlay.fadeIn()
                    # Add a small delay to ensure the overlay is visible
                    QTimer.singleShot(100, self.return_to_shopping)
            
        except Exception as e:
            print(f"Error setting up QR generation: {e}")
            self.qr_label.setText("Failed to load QR Code")
            # Ensure cleanup happens even if QR fails
            self.cleanup_resources()
            
            # Show transition overlay before returning to shopping
            if not hasattr(self, 'transition_in_progress') or not self.transition_in_progress:
                self.transition_in_progress = True
                self.transition_overlay.fadeIn()
                # Add a small delay to ensure the overlay is visible
                QTimer.singleShot(100, self.return_to_shopping)

    def cancel_payment(self):
        """Handle cancel payment action with API call"""
        # Prevent multiple clicks
        if hasattr(self, 'processing_action') and self.processing_action:
            print("Already processing an action, ignoring click")
            return
            
        self.processing_action = True
        
        cancel_start = time.time()
        print(f"[QR_TIMING] Starting cancel payment at: {cancel_start}")
        
        # Check if already in transition
        if hasattr(self, 'transition_in_progress') and self.transition_in_progress:
            return
            
        self.transition_in_progress = True
        
        # Disable button to prevent multiple clicks
        self.cancel_button.setEnabled(False)
        
        # Stop transaction check and countdown immediately
        self.stop_transaction_check.set()
        self.countdown_timer.stop()
        print(f"[QR_TIMING] Stopped monitoring at: {time.time() - cancel_start:.4f}s")
        
        # Send cancel signal in background thread
        def send_cancel_signal():
            try:
                url = f"{CART_CANCEL_PAYMENT_SIGNAL}{DEVICE_ID}/"
                print(f"[QR_TIMING] Sending cancel API request to: {url}")
                response = requests.post(url)
                print(f"[QR_TIMING] Cancel payment signal sent: {response.status_code} at {time.time() - cancel_start:.4f}s")
            except Exception as e:
                print(f"Error sending cancel signal: {e}")
                
        # Start API thread
        cancel_thread = Thread(target=send_cancel_signal, daemon=True)
        cancel_thread.start()
        
        # Import here to avoid circular imports
        from page4_shopping import ShoppingPage
        
        # Create shopping page
        self.shopping_page = ShoppingPage()
        
        # Define transition completion handler
        def show_new_page():
            # Show shopping page
            self.shopping_page.show()
            
            # Fade out overlay and close QR page
            self.transition_overlay.fadeOut(lambda: self.close())
        
        # Show transition overlay first, then show new page after fade in completes
        self.transition_overlay.fadeIn(show_new_page)

    def return_to_shopping(self):
        """Enhanced return to shopping with smooth transition"""
        return_start = time.time()
        print(f"[QR_TIMING] Starting return to shopping at: {return_start}")
        
        # Check if already in transition
        if hasattr(self, 'transition_in_progress') and self.transition_in_progress:
            return
            
        self.transition_in_progress = True
        
        # Import here to avoid circular imports
        from page4_shopping import ShoppingPage
        
        # Create shopping page
        self.shopping_page = ShoppingPage()
        
        # Define transition completion handler
        def show_new_page():
            # Show shopping page
            self.shopping_page.show()
            
            # Fade out overlay and close QR page
            self.transition_overlay.fadeOut(lambda: self.close())
        
        # Show transition overlay first, then show new page after fade in completes
        self.transition_overlay.fadeIn(show_new_page)
        
        # Clean up resources in background to avoid lag
        def cleanup_resources_bg():
            try:
                self.cleanup_resources()
                print(f"[QR_TIMING] Resources cleaned up at: {time.time() - return_start:.4f}s")
            except Exception as e:
                print(f"Error in cleanup: {e}")
                
        # Start cleanup in background (non-blocking)
        cleanup_thread = Thread(target=cleanup_resources_bg, daemon=True)
        cleanup_thread.start()

    def cleanup_resources(self):
        """Clean up resources before closing"""
        if self.countdown_timer:
            self.countdown_timer.stop()
        self.stop_transaction_check.set()  # Ensure transaction check is stopped
        # Clean up any other resources

    def start_transaction_check(self):
        check_thread = Thread(
            target=self.check_transaction,
            args=(self.total_amount,),  # Pass the integer amount
            daemon=True
        )
        check_thread.start()

    def check_transaction(self, amount):
        # Force CPU configuration at start of thread
        self.configure_device()
        
        USERNAME = "0375712517"
        PASSWORD = "Ngo252002@"
        account_no = "0375712517"

        mb = None
        # Store the transfer content for later use
        self.transfer_content = ""
        
        try:
            print("Khởi tạo kết nối...")
            mb = MBBank(username=USERNAME, password=PASSWORD)
            
            # Add a timeout for authentication to prevent hanging
            auth_timeout = 10  # seconds
            auth_start = time.time()
            
            print("Đang đăng nhập...")
            try:
                # Set a timeout for authentication
                if time.time() - auth_start > auth_timeout:
                    print("Authentication timed out, proceeding anyway")
                else:
                    mb._authenticate()
                    print("Xác thực thành công!")
            except Exception as auth_e:
                print(f"Authentication error: {auth_e}, will retry once")
                try:
                    # One retry with shorter timeout
                    mb = MBBank(username=USERNAME, password=PASSWORD)
                    mb._authenticate()
                    print("Xác thực thành công sau khi thử lại!")
                except:
                    print("Authentication failed after retry, proceeding with limited functionality")
            
            print(f"\nBat dau theo doi giao dịch:")
            print(f"- Đề xuất: {amount:,} VND")
            print(f"- Từ thời điểm: {self.qr_start_time.strftime('%d/%m/%Y %H:%M:%S')}")
            
            while not self.stop_transaction_check.is_set():
                try:
                    current_time = datetime.now()
                    # Get transactions since QR creation
                    transactions = mb.getTransactionAccountHistory(
                        accountNo=account_no,
                        from_date=self.qr_start_time,
                        to_date=current_time
                    )
                    
                    if transactions and 'transactionHistoryList' in transactions:
                        trans_list = transactions['transactionHistoryList']
                        
                        for trans in trans_list:
                            try:
                                credit = int(trans.get('creditAmount', '0'))
                                debit = int(trans.get('debitAmount', '0'))
                                trans_time = datetime.strptime(trans.get('transactionDate', ''), '%d/%m/%Y %H:%M:%S')
                                trans_id = trans.get('refNo', '')
                                description = trans.get('description', 'N/A')
                                
                                # Check conditions:
                                # 1. Is credit transaction (credit > 0, debit = 0)
                                # 2. Transaction time after QR creation
                                # 3. Transaction not processed before
                                if (credit > 0 and debit == 0 and
                                    trans_time > self.qr_start_time and
                                    trans_id not in self.processed_transaction_ids):
                                    
                                    self.processed_transaction_ids.add(trans_id)
                                    print("\n" + "="*50)
                                    print(f"Phat hien giao dich ({current_time.strftime('%H:%M:%S')})")
                                    print(f"Thoi gian GD: {trans_time.strftime('%d/%m/%Y %H:%M:%S')}")
                                    print(f"So tien nhan: +{credit:,} VND")
                                    print(f"Tu: {trans.get('benAccountName', 'N/A')}")
                                    print(f"Noi dung: {description}")
                                    print(f"Ma GD: {trans_id}")
                                    print("="*50)
                                    
                                    # Store the donation amount for success page
                                    QRCodePage.donation_amount = credit
                                    
                                    # Store the transfer content for the note field
                                    QRCodePage.transfer_content = description
                                    
                                    # Emit signal to switch to success page
                                    self.switch_to_success.emit()
                                    return
                                    
                            except Exception as e:
                                print(f"Error processing transaction: {e}")
                                continue
                    
                    time.sleep(0.2)
                    
                except Exception as e:
                    print(f"Error checking transactions: {e}")
                    time.sleep(1)
                    continue
                    
        except Exception as e:
            print(f"Lỗi khởi tạo: {str(e)}")
        finally:
            if mb:
                try:
                    print("Đang đăng xuất...")
                    mb._req.close()
                except:
                    pass

    def handle_success(self):
        def switch_page():
            start_time = PageTiming.start_timing()
            self.countdown_timer.stop()
            from page6_success import SuccessPage
            self.success_page = SuccessPage()
            self.payment_completed.emit(True)
            
            def show_new_page():
                self.success_page.show()
                self.transition_overlay.fadeOut(lambda: self.close())
                PageTiming.end_timing(start_time, "QRCodePage", "SuccessPage")
            
            # Only play sounds if there's an actual donation
            if QRCodePage.donation_amount > 0:
                sound_path_ting = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sound', 'ting-ting.wav'))
                sound_path_payment = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sound', 'sucesspayment.wav'))
                
                try:
                    # Play first sound (ting-ting)
                    self.ting_sound = QSoundEffect()
                    self.ting_sound.setSource(QUrl.fromLocalFile(sound_path_ting))
                    self.ting_sound.setVolume(1.0)
                    
                    def play_payment_and_speak():
                        # Play payment success sound
                        self.payment_sound = QSoundEffect()
                        self.payment_sound.setSource(QUrl.fromLocalFile(sound_path_payment))
                        self.payment_sound.setVolume(1.0)
                        self.payment_sound.play()
                        
                        # Wait for payment sound then speak amount
                        def speak_amount():
                            try:
                                # Use the collected donation amount
                                amount = QRCodePage.donation_amount
                                amount_words = self.number_to_vietnamese(amount)
                                print(f"Speaking amount: {amount} ({amount_words})")  # Debug print
                                
                                # Only speak if there's an amount (redundant check but kept for safety)
                                if amount > 0:
                                    # Chỉ đọc số tiền với tốc độ chậm hơn (100 từ/phút)
                                    subprocess.run(['espeak', '-vvi', '-s100', '-g5', amount_words + ' đồng'])
                            except Exception as e:
                                print(f"Error speaking amount: {e}")
                        
                        # Tăng delay lên 2500ms để đảm bảo âm thanh sucesspayment.wav phát xong
                        QTimer.singleShot(2500, speak_amount)
                    
                    # Start the sequence
                    self.ting_sound.play()
                    QTimer.singleShot(1000, play_payment_and_speak)
                    
                    # Increase transition delay for sound to complete
                    QTimer.singleShot(5000, lambda: self.transition_overlay.fadeIn(show_new_page))
                    
                except Exception as e:
                    print(f"Error playing sounds: {e}")
                    # If sound fails, still show success page without delay
                    QTimer.singleShot(500, lambda: self.transition_overlay.fadeIn(show_new_page))
            else:
                # For No Banking (zero donation), transition quickly without sound
                print("No donation amount - skipping sounds")
                QTimer.singleShot(500, lambda: self.transition_overlay.fadeIn(show_new_page))
                
        switch_page()

    def number_to_vietnamese(self, number):
        """Chuyển số thành chữ tiếng Việt"""
        units = ["", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
        teen = ["mười", "mười một", "mười hai", "mười ba", "mười bốn", "mười lăm", "mười sáu", "mười bảy", "mười tám", "mười chín"]
        tens = ["", "mười", "hai mươi", "ba mươi", "bốn mươi", "năm mươi", "sáu mươi", "bảy mươi", "tám mươi", "chín mươi"]
        
        if number == 0:
            return "không"
            
        def read_group(n):
            hundreds = n // 100
            remainder = n % 100
            tens_digit = remainder // 10
            ones_digit = remainder % 10
            
            result = []
            if hundreds > 0:
                result.append(f"{units[hundreds]} trăm")
            if tens_digit > 0:
                if tens_digit == 1:
                    result.append(teen[ones_digit])
                    return " ".join(result)
                result.append(tens[tens_digit])
            if ones_digit > 0:
                if tens_digit > 1 and ones_digit == 1:
                    result.append("mốt")
                elif tens_digit > 0 and ones_digit == 5:
                    result.append("lăm")
                else:
                    result.append(units[ones_digit])
            elif tens_digit > 0:
                result.append("")
            return " ".join(result)
        
        groups = []
        group_names = ["", "nghìn", "triệu", "tỷ"]
        
        if number == 0:
            return "không"
            
        number_str = str(number)
        while number_str:
            groups.append(number_str[-3:] if len(number_str) >= 3 else number_str)
            number_str = number_str[:-3]
            
        result = []
        for i, group in enumerate(groups):
            group_value = int(group)
            if group_value > 0:
                group_text = read_group(group_value)
                if group_names[i]:
                    group_text += f" {group_names[i]}"
                result.append(group_text)
                
        return " ".join(reversed(result))

    def update_countdown(self):
        """Update the countdown timer display"""
        current_time = datetime.now()
        elapsed = current_time - self.target_time
        remaining = self.countdown_seconds - elapsed.total_seconds()
        
        if remaining <= 0:
            self.countdown_timer.stop()
            self.countdown_label.setText(_("qrCodePage.qrExpired"))
            
            # When timer expires, trigger No Banking flow instead of returning to shopping
            print("Timer expired - proceeding with No Banking flow")
            QRCodePage.donation_amount = 0
            self.stop_transaction_check.set()
            
            # Check if already in transition
            if not hasattr(self, 'transition_in_progress') or not self.transition_in_progress:
                self.transition_in_progress = True
                
                # Switch to success page with zero donation
                self.switch_to_success.emit()
            return
            
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        self.countdown_label.setText(f"{_('qrCodePage.timeRemaining')}{minutes:02d}:{seconds:02d}")

    def read_amount(self):
        """Read the total amount using TTS"""
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)  # Set speech rate
            engine.setProperty('volume', 1.0)  # Set volume level

            # Format the amount for reading
            amount_text = f"{self.total_amount:,}".replace(",", ".")  # Format with dots for thousands
            message = f"Số tiền là {amount_text} đồng."
            print(f"Reading amount: {message}")  # Debug print

            engine.say(message)
            engine.runAndWait()
        except Exception as e:
            print(f"Error reading amount: {e}")

    def closeEvent(self, event):
        self.cleanup_resources()
        event.accept()

    def no_banking(self):
        """Handle the No Banking button click - go directly to success page with zero amount"""
        # Prevent multiple clicks
        if hasattr(self, 'processing_action') and self.processing_action:
            print("Already processing a No Banking action, ignoring click")
            return
            
        self.processing_action = True
        print("No Banking selected - proceeding with zero donation amount")
        
        # Set donation amount to 0
        QRCodePage.donation_amount = 0
        
        # Set a special transfer content for Heartfelt Support
        QRCodePage.transfer_content = "Heartfelt support donation"
        
        # Stop transaction check and countdown
        self.stop_transaction_check.set()
        if self.countdown_timer:
            self.countdown_timer.stop()
        
        # Disable button to prevent multiple clicks
        self.no_banking_button.setEnabled(False)
        
        # Switch to success page
        self.switch_to_success.emit()

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = QRCodePage()
    window.show()
    sys.exit(app.exec_())
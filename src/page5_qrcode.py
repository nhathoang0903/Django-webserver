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
from PyQt5.QtMultimedia import QSoundEffect 
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
# import pyttsx3 
# import qrcode
# from vietqr.VietQR import genQRString, getBincode

from config import CART_CANCEL_PAYMENT_SIGNAL, DEVICE_ID
from utils.translation import _, get_current_language

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
        
        # Define common size for QR code and charity image - Greatly increased for 1900x1080 window
        self.common_size = 550  # Massively increased from 400 for better display on larger screen
        
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
        self.countdown_seconds = 90  # Reduced to 1.5minute
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

        # Define common button size - Greatly increased for 1900x1080 window
        button_width = 400  # Massively increased from 300
        button_height = 100  # Massively increased from 80

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)  # Further increased margins

        # Left Section - Will now contain QR code and information
        left_section = QWidget()
        left_layout = QVBoxLayout(left_section)
        # Adjust margins for larger components
        left_layout.setContentsMargins(30, 20, 30, 20)  # Further increased margins
        left_layout.setSpacing(20)  # Further increased spacing for larger screen

        # QR Code Section - Create a separate section for QR code with good spacing
        qr_section = QWidget()
        qr_section_layout = QVBoxLayout(qr_section)
        qr_section_layout.setContentsMargins(0, 0, 0, 0)
        qr_section_layout.setAlignment(Qt.AlignCenter)

        # QR Code Container - create a separate container with custom size
        qr_container = QWidget()
        # Make the container more flexible to accommodate the full QR image
        qr_container.setMinimumHeight(self.common_size)
        qr_container_layout = QVBoxLayout(qr_container)
        qr_container_layout.setContentsMargins(0, 0, 0, 0)
        qr_container_layout.setSpacing(0)
        qr_container_layout.setAlignment(Qt.AlignCenter)

        # QR Code Frame with adjusted size
        self.qr_frame = QFrame()
        # Make the frame more flexible to accommodate the full image
        self.qr_frame.setMinimumSize(self.common_size, self.common_size)
        self.qr_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        
        # QR Code Label
        self.qr_label = QLabel(self.qr_frame)
        self.qr_label.setAlignment(Qt.AlignCenter)
        # Don't set a fixed size for the QR label to allow flexible sizing based on image content
        self.qr_label.setText(_("qrCodePage.loading"))
        self.qr_label.setStyleSheet("background-color: transparent; font-size: 32px;")  # Further increased font size
        
        # Add QR code to container with center alignment
        qr_container_layout.addWidget(self.qr_frame, 0, Qt.AlignCenter)
        
        # Add QR container to QR section
        qr_section_layout.addWidget(qr_container, 1, Qt.AlignCenter)
        
        # Add QR section to main layout - QR now dominates the upper part
        left_layout.addWidget(qr_section, 4)  # QR takes 4/6 of vertical space
        
        # Bottom container for all info and buttons - takes less space now
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 10, 0, 10)  # Added top/bottom padding
        bottom_layout.setSpacing(15)  # Reduced spacing slightly to fit everything
        
        # Payment Details Container - smaller and compact
        details_frame = QFrame()
        details_frame.setStyleSheet("""
            background-color: transparent;
        """)
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(0, 0, 0, 0)  # Remove internal margins
        details_layout.setSpacing(10)  # Slightly reduced spacing

        # Amount with increased font
        self.amount_label = QLabel()
        self.amount_label.setFont(QFont("Inria Sans", 22, QFont.Bold))  # Slightly reduced font size
        amount_text = sum(float(product['price']) * quantity 
                         for product, quantity in self.cart_state.cart_items)
        self.amount_label.setText(f"{_('qrCodePage.amount')}{'{:,.0f}'.format(amount_text).replace(',', '.')} vnđ")

        # Account number - new information
        account_number = "0375712517"
        account_label = QLabel(f"{_('qrCodePage.accountNumber')}{account_number}")
        account_label.setFont(QFont("Inria Sans", 22, QFont.Bold))  # Slightly reduced font size
        
        # Account Details - increased font
        acc_name_label = QLabel(_("qrCodePage.accountName"))
        acc_name_label.setFont(QFont("Inria Sans", 22))  # Slightly reduced font size
        
        bank_label = QLabel(_("qrCodePage.bankName"))
        bank_label.setFont(QFont("Inria Sans", 22))  # Slightly reduced font size

        # Add all labels to details layout
        for label in [self.amount_label, account_label, acc_name_label, bank_label]:
            label.setAlignment(Qt.AlignCenter)
            details_layout.addWidget(label)
  
        # Add details frame to bottom layout
        bottom_layout.addWidget(details_frame, alignment=Qt.AlignCenter)
        
        # Minimal spacing between info and time
        bottom_layout.addSpacing(15)  # Increased spacing
        
        # Countdown and generation time - change back to vertical layout
        time_container = QWidget()
        time_layout = QVBoxLayout(time_container)  # Changed back to vertical layout
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(10)  # Spacing between countdown and generation time
        
        # Countdown label
        self.countdown_label = QLabel()
        self.countdown_label.setFont(QFont("Inria Sans", 22, QFont.Bold))
        self.countdown_label.setStyleSheet("color: #D30E11;")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.hide()

        # Generation time label
        self.gen_time_label = QLabel()
        italic_font = QFont("Inria Sans", 22)
        italic_font.setItalic(True)
        self.gen_time_label.setFont(italic_font)
        self.gen_time_label.setAlignment(Qt.AlignCenter)
        self.gen_time_label.hide()
        
        # Add labels to time container vertically (one below the other)
        time_layout.addWidget(self.countdown_label, alignment=Qt.AlignCenter)
        time_layout.addWidget(self.gen_time_label, alignment=Qt.AlignCenter)
        
        # Add time container to bottom layout
        bottom_layout.addWidget(time_container, alignment=Qt.AlignCenter)
        
        # Add more spacing to push button down
        bottom_layout.addSpacing(15)
        
        # Cancel Payment button - use common button size
        self.cancel_button = QPushButton(_("qrCodePage.cancelPayment"))
        self.cancel_button.setFont(QFont("Josefin Sans", 28, QFont.Bold))
        self.cancel_button.setFixedSize(button_width, button_height)
        self.cancel_button.setStyleSheet("""
            background-color: #416FFA;
            color: white;
            border-radius:25px;
        """)
        self.cancel_button.clicked.connect(self.cancel_payment)
        bottom_layout.addWidget(self.cancel_button, alignment=Qt.AlignCenter)
        
        # Add the bottom container to main layout
        left_layout.addWidget(bottom_container, 2)  # Takes 2/6 of vertical space

        # Add left section to main layout
        main_layout.addWidget(left_section)

        # Right Section - Will now contain charity image and message
        right_section = QWidget()
        right_layout = QVBoxLayout(right_section)
        right_layout.setContentsMargins(30, 0, 30, 20)  # Giảm top margin từ 20 xuống 0
        right_layout.setSpacing(5)  # Giảm spacing từ 10 xuống 5
        
        # Thêm spacer phía trên để đẩy ảnh lên cao hơn
        right_layout.addSpacing(90)  # Tăng từ 60 lên 90
        
        # Charity image section - takes most of the space
        charity_section = QWidget()
        charity_section.setContentsMargins(0, 0, 0, 0)  # Set margins trực tiếp cho widget
        charity_section_layout = QVBoxLayout(charity_section)
        charity_section_layout.setContentsMargins(0, 0, 0, 0)
        charity_section_layout.setSpacing(0)  # Giảm spacing xuống 0
        charity_section_layout.setAlignment(Qt.AlignCenter | Qt.AlignTop)  # Thêm AlignTop để đẩy lên cao
        
        # Charity image container - match QR code container
        charity_container = QWidget()
        charity_container.setFixedHeight(self.common_size)  # Giảm chiều cao xuống
        charity_layout = QVBoxLayout(charity_container)
        charity_layout.setContentsMargins(0, 0, 0, 40)  # Tăng bottom margin từ 30 lên 40
        charity_layout.setSpacing(0)
        charity_layout.setAlignment(Qt.AlignCenter | Qt.AlignTop)  # Thêm AlignTop

        # Charity image
        charity_label = QLabel()
        charity_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'lovecharity.png')
        charity_pixmap = QPixmap(charity_path)
        
        if not charity_pixmap.isNull():
            charity_label.setPixmap(charity_pixmap.scaled(self.common_size, self.common_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            charity_label.setText("Charity Image")
            charity_label.setStyleSheet("font-size: 32px; color: #507849;")
            
        charity_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)  # Thêm AlignTop
        charity_label.setFixedSize(self.common_size, self.common_size)  # Match QR code size
        charity_layout.addWidget(charity_label, 0, Qt.AlignCenter | Qt.AlignTop)  # Thêm 0 làm stretch và AlignTop
        
        # Add charity container to charity section
        charity_section_layout.addWidget(charity_container, 0, Qt.AlignCenter | Qt.AlignTop)  # Thêm 0 làm stretch
        
        # Add charity section to right layout - charity image dominates upper part
        right_layout.addWidget(charity_section, 7)  # Tăng từ 6 lên 7 để ưu tiên phần ảnh hơn nữa
        
        # Message and button container - takes less space now
        message_button_container = QWidget()
        message_button_layout = QVBoxLayout(message_button_container)
        message_button_layout.setContentsMargins(0, 0, 0, 5)  # Giảm bottom padding từ 10 xuống 5
        message_button_layout.setSpacing(5)  # Giảm spacing từ 10 xuống 5
        
        # Message container with charity message
        message_container = QWidget()
        message_layout = QVBoxLayout(message_container)
        message_layout.setContentsMargins(0, 0, 0, 0)
        
        # Charity message với kích thước phù hợp cho 2 dòng
        self.message_label = QLabel(_("qrCodePage.charityMessage"))
        message_font = QFont("Josefin Sans", 26)
        message_font.setItalic(True)
        self.message_label.setFont(message_font)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)
        
        # Cách tính chiều cao chính xác cho 2 dòng
        fm = QFontMetrics(message_font)
        line_spacing = fm.lineSpacing()  # Khoảng cách giữa các dòng
        text_height = line_spacing * 2  # Chiều cao cho 2 dòng
        
        # Tính toán chiều rộng tối thiểu để đảm bảo hiển thị đủ nội dung
        text = _("qrCodePage.charityMessage")
        text_width = fm.horizontalAdvance(text)
        
        # Thêm padding cho đủ không gian hiển thị
        padding_height = 16
        padding_width = 40  # Thêm padding cho chiều rộng
        
        # Set kích thước cố định cho label để đảm bảo hiển thị đủ nội dung
        self.message_label.setMinimumHeight(text_height + padding_height)
        self.message_label.setMaximumHeight(text_height + padding_height)
        
        # Đặt chiều rộng tối thiểu cho label (ít nhất 80% chiều rộng của text)
        min_width = max(800, int(text_width * 0.8))
        self.message_label.setMinimumWidth(min_width + padding_width)
        
        # Đặt chiều rộng tối đa để tránh quá rộng
        max_width = 900  # Điều chỉnh nếu cần
        self.message_label.setMaximumWidth(max_width)
        
        self.message_label.setStyleSheet("""
            color: #D30E11; 
            margin: 0px; 
            padding: 8px;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
        """)
        
        message_layout.addWidget(self.message_label, alignment=Qt.AlignCenter)
        message_button_layout.addWidget(message_container, 1, Qt.AlignCenter)
        
        # Add more spacing to push No Banking button down
        message_button_layout.addSpacing(30)
        
        # No Banking button 
        self.no_banking_button = QPushButton(_("qrCodePage.heartfeltSupport"))
        self.no_banking_button.setFont(QFont("Josefin Sans", 28, QFont.Bold))
        self.no_banking_button.setFixedSize(button_width, button_height)
        self.no_banking_button.setStyleSheet("""
            background-color: #EB1CBA;
            color: white;
            border-radius:25px;
        """)
        self.no_banking_button.clicked.connect(self.no_banking)
        message_button_layout.addWidget(self.no_banking_button, alignment=Qt.AlignCenter)
        
        # Add message and button container to right layout
        right_layout.addWidget(message_button_container, 2)  # Takes 2/6 of vertical space
        
        # Add right section to main layout
        main_layout.addWidget(right_section)

    def load_qr_code(self):
        """Optimized QR code loading from static image"""
        qr_start = time.time()
        print(f"[QR_TIMING] Starting QR code loading at: {qr_start}")
        
        try:
            # Set the start time when QR is shown
            self.qr_start_time = datetime.now()
            self.target_time = datetime.now() + timedelta(seconds=self.countdown_seconds)
            
            # First just show a placeholder and start the countdown
            # This ensures UI is responsive immediately
            self.countdown_timer.start(1000)
            self.countdown_label.show()
            print(f"[QR_TIMING] Countdown started at: {time.time() - qr_start:.4f}s")
            
            # Process events to keep UI responsive
            QApplication.processEvents()
            
            try:
                # Load static QR code image instead of generating one
                qr_image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'qr-code-banking.png')
                print(f"[QR_TIMING] Loading QR code from: {qr_image_path}")
                
                # Load QR image in a separate timer to avoid blocking UI
                def load_and_display_qr():
                    try:
                        # Load QR image
                        qr_pixmap = QPixmap(qr_image_path)
                        if qr_pixmap.isNull():
                            raise Exception(f"Failed to load QR code image from {qr_image_path}")
                        
                        print(f"[QR_TIMING] QR image loaded at: {time.time() - qr_start:.4f}s")
                        
                        # Get original dimensions
                        original_width = qr_pixmap.width()
                        original_height = qr_pixmap.height()
                        print(f"[QR_TIMING] Original image dimensions: {original_width}x{original_height}")
                        
                        display_size = self.common_size * 0.97 
                        scale_factor = min(display_size / original_width, display_size / original_height)
                        new_width = int(original_width * scale_factor)
                        new_height = int(original_height * scale_factor)
                        
                        # Scale the image
                        scaled_pixmap = qr_pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        
                        # Adjust the QR label size to match the scaled image size exactly
                        self.qr_label.setFixedSize(new_width, new_height)
                        
                        # Set the scaled image
                        self.qr_label.setPixmap(scaled_pixmap)
                        self.qr_label.setAlignment(Qt.AlignCenter)
                        print(f"[QR_TIMING] QR image displayed at scaled size: {new_width}x{new_height}")
                        print(f"[QR_TIMING] QR image displayed at: {time.time() - qr_start:.4f}s")
                        
                        # Update date/time display
                        current_time = QDateTime.currentDateTime()
                        time_str = current_time.toString('hh:mm:ss')
                        day = current_time.date().day()
                        month = current_time.date().month()
                        year = current_time.date().year()
                        
                        # Format date based on language
                        current_language = get_current_language()
                        
                        if current_language == "en":
                            month_str = current_time.toString('MMM')
                            
                            # Get ordinal suffix
                            if day in [1, 21, 31]:
                                suffix = "st"
                            elif day in [2, 22]:
                                suffix = "nd"
                            elif day in [3, 23]:
                                suffix = "rd"
                            else:
                                suffix = "th"
                            
                            date_str = f"{month_str} {day}<sup>{suffix}</sup>, {year}"
                        
                        elif current_language == "vi":
                            date_str = f"{day} tháng {month} năm {year}"
                        
                        elif current_language == "ja":
                            date_str = f"{year}年{month}月{day}日"
                        
                        elif current_language == "fr":
                            months_fr = ["janvier", "février", "mars", "avril", "mai", "juin", 
                                       "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
                            month_name = months_fr[month - 1]
                            
                            if day == 1:
                                date_str = f"1er {month_name} {year}"
                            else:
                                date_str = f"{day} {month_name} {year}"
                        
                        else:
                            # Default fallback (English style without suffix)
                            month_str = current_time.toString('MMM')
                            date_str = f"{month_str} {day}, {year}"
                        
                        # Combine time and date
                        formatted_datetime = f"{_('qrCodePage.generated')}{time_str}, {date_str}"
                        
                        self.gen_time_label.setText(formatted_datetime)
                        self.gen_time_label.setTextFormat(Qt.RichText)
                        self.gen_time_label.show()
                        print(f"[QR_TIMING] Generation time displayed at: {time.time() - qr_start:.4f}s")
                        
                        # Start transaction check with delay
                        print(f"[QR_TIMING] Transaction check scheduled to start in 10 seconds")
                        QTimer.singleShot(10000, self.start_transaction_check)
                        
                        print(f"[QR_TIMING] Total QR code loading time: {time.time() - qr_start:.4f}s")
                    except Exception as inner_e:
                        print(f"Error displaying QR: {inner_e}")
                        self.qr_label.setText(f"Error loading QR code")
                        QApplication.processEvents()
                
                # Call the load function after a small delay to ensure UI is responsive
                QTimer.singleShot(50, load_and_display_qr)
                
            except Exception as e:
                print(f"Error in QR loading: {e}")
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
            print(f"Error setting up QR loading: {e}")
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
        """Hủy thanh toán và quay về trang mua hàng"""
        # Handle cancellation and navigation logic
        if not self.processing_action:
            self.processing_action = True
            
            # Stop the transaction check thread 
            self.stop_transaction_check.set()
            print("Stopped transaction check thread")
            
            # Stop the countdown timer
            if hasattr(self, 'countdown_timer') and self.countdown_timer.isActive():
                self.countdown_timer.stop()
            
            # Hide countdown label
            if hasattr(self, 'countdown_label'):
                self.countdown_label.hide()
                
            # Send cancellation signal to server
            self.send_cancel_signal_to_server()
                
            # Disable buttons during transition
            if hasattr(self, 'cancel_button'):
                self.cancel_button.setEnabled(False)
            if hasattr(self, 'no_banking_button'):
                self.no_banking_button.setEnabled(False)
                
            # Return to shopping page
            QTimer.singleShot(300, self.return_to_shopping)  

    def send_cancel_signal_to_server(self):
        """Gửi tín hiệu hủy thanh toán đến server"""
        try:
            # Vô hiệu hóa API call
            print("Cancel payment signal - API call DISABLED")
            # url = f"{CART_CANCEL_PAYMENT_SIGNAL}{DEVICE_ID}/"
            # print(f"Sending cancel payment signal to: {url}")
            # response = requests.post(url)
            
            # if response.status_code == 200:
            #     print("Cancel payment signal sent successfully")
            # else:
            #     print(f"Error sending cancel payment signal: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"Error sending cancel payment signal: {e}")
        
    def return_to_shopping(self):
        """Return to shopping page with transition effects"""
        # Prevent multiple calls
        if hasattr(self, 'transition_in_progress') and self.transition_in_progress:
            print("Transition already in progress, ignoring duplicate return request")
            return
            
        print("Starting transition to shopping page")
        self.transition_in_progress = True
        
        # Stop all background processes first before starting page transition
        self.cleanup_resources()
        
        # Show transition overlay BEFORE importing and creating the next page
        # to avoid UI freezing during page creation
        self.transition_overlay.fadeIn()
        
        # Use a small delay to ensure the overlay is shown before heavy operations
        def create_and_show_shopping_page():
            try:
                # Import here to avoid circular imports
                from page4_shopping import ShoppingPage
                
                # Process events to keep UI responsive during page creation
                QApplication.processEvents()
                
                print("Creating new shopping page")
                self.shopping_page = ShoppingPage()
                
                # Define transition completion handler
                def show_new_page():
                    print("Showing shopping page")
                    # Show shopping page
                    self.shopping_page.show()
                    
                    # Fade out overlay and close QR page
                    self.transition_overlay.fadeOut(lambda: self.close())
                
                # The overlay is already showing, just call the show handler directly
                # Process events one more time before showing the page
                QApplication.processEvents()
                show_new_page()
                
            except Exception as e:
                print(f"Error returning to shopping page: {e}")
                import traceback
                traceback.print_exc()
                
                # Emergency fallback if transition fails
                try:
                    from page1_welcome import WelcomePage
                    welcome = WelcomePage()
                    welcome.show()
                    self.close()
                except:
                    print("Critical error: Unable to navigate to any page")
                    self.close()
        
        # Use QTimer to ensure overlay is shown first
        QTimer.singleShot(100, create_and_show_shopping_page)

    def cleanup_resources(self):
        """Clean up resources before closing"""
        print("Starting thorough resource cleanup...")
        
        # Stop all timers
        if hasattr(self, 'countdown_timer') and self.countdown_timer:
            if self.countdown_timer.isActive():
                print("Stopping countdown timer")
                self.countdown_timer.stop()
        
        # Stop transaction check thread
        if hasattr(self, 'stop_transaction_check'):
            print("Setting thread stop event")
            self.stop_transaction_check.set()
            
        # Wait a bit for threads to acknowledge stop signal
        print("Waiting for threads to stop...")
        QApplication.processEvents()
        time.sleep(0.2)
        
        # Force garbage collection to release memory
        print("Running garbage collection")
        gc.collect()
        
        # Clear any large objects
        if hasattr(self, 'qr_label') and self.qr_label:
            self.qr_label.clear()
        
        print("Resource cleanup completed")

    def start_transaction_check(self):
        """Start transaction check thread with improved error handling"""
        try:
            # Create a thread to check for transactions without blocking UI
            print("Starting transaction check thread in background")
            check_thread = Thread(
                target=self.check_transaction,
                args=(self.total_amount,),  # Pass the integer amount
                daemon=True
            )
            check_thread.start()
            
            # Set a fallback timer - if bank authentication fails, we'll 
            # automatically use no-banking mode when this timer expires
            print("Setting 60-second fallback timer for no-banking mode")
            QTimer.singleShot(60000, self.handle_auth_timeout)
            
        except Exception as e:
            print(f"Error starting transaction check thread: {e}")
            # No need to show error to user, the fallback timer will handle it

    def handle_auth_timeout(self):
        """Handle case where bank authentication takes too long"""
        # Only proceed if:
        # 1. We're not already in a transition
        # 2. The QR page is still visible
        # 3. No transaction has been detected yet
        if (not hasattr(self, 'transition_in_progress') or not self.transition_in_progress) and \
           self.isVisible() and \
           QRCodePage.donation_amount == 0:
            
            print("Bank authentication timed out - proceeding with no-banking flow")
            
            # First stop any ongoing transaction check
            self.stop_transaction_check.set()
            
            # Set donation amount to 0 for no-banking flow
            QRCodePage.donation_amount = 0
            QRCodePage.transfer_content = "Heartfelt support donation"
            
            # Start no-banking flow (delayed slightly to ensure UI responsiveness)
            QTimer.singleShot(100, lambda: self.switch_to_success.emit())

    def check_transaction(self, amount):
        """Check for incoming transactions in a thread with improved error handling"""
        # Force CPU configuration at start of thread
        self.configure_device()
        
        # Import asyncio và thiết lập event loop mới trong thread
        import asyncio
        
        # Tạo event loop mới trong thread hiện tại
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            print("Created new event loop for transaction checking thread")
        except Exception as e:
            print(f"Error setting up event loop: {e}")
            return  # Exit early if we can't set up event loop
        
        USERNAME = "0375712517"
        PASSWORD = "Ngo252002@"
        account_no = "0375712517"

        mb = None
        authenticated = False
        # Store the transfer content for later use
        self.transfer_content = ""
        
        # Connection retry parameters - reduce retries to avoid long blocking
        max_connection_retries = 2  # Reduced from 3
        connection_retry_count = 0
        
        # Transaction check parameters
        max_check_retries = 3  # Reduced from 5
        check_retry_count = 0
        check_interval = 1.0  # Time between checks in seconds
        
        try:
            print("Khởi tạo kết nối...")
            
            # First attempt - don't retry immediately to avoid UI freezing
            try:
                # Set timeout before creating MBBank to avoid hanging
                auth_timeout = 15  # seconds - give it more time for first attempt
                
                # Create a new instance
                print(f"Đang đăng nhập... (attempt {connection_retry_count + 1}/{max_connection_retries})")
                mb = MBBank(username=USERNAME, password=PASSWORD)
                
                # Try authentication once with timeout
                auth_start = time.time()
                auth_complete = False
                
                # Set up a timeout check
                while not auth_complete and time.time() - auth_start < auth_timeout and not self.stop_transaction_check.is_set():
                    try:
                        # Try to authenticate
                        mb._authenticate()
                        auth_complete = True
                        authenticated = True
                        print("Xác thực thành công!")
                    except Exception as inner_e:
                        # If it fails immediately, wait a bit before retry
                        print(f"Authentication retry: {inner_e}")
                        time.sleep(0.5)
                
                # If timed out or stopped, clean up
                if not auth_complete:
                    print("Authentication timed out or thread stopping")
                    if mb:
                        if hasattr(mb, '_req') and mb._req is not None:
                            mb._req.close()
                        mb = None
                
            except Exception as auth_e:
                print(f"Initial authentication error: {auth_e}")
                if mb:
                    try:
                        if hasattr(mb, '_req') and mb._req is not None:
                            mb._req.close()
                    except:
                        pass
                    mb = None
            
            # If first attempt failed, don't retry immediately - this prevents UI freezing
            # The fallback timer will handle the case where authentication fails
            
            # If authentication succeeded, proceed with transaction monitoring
            if authenticated and mb is not None:
                print(f"\nBắt đầu theo dõi giao dịch:")
                print(f"- Đề xuất: {amount:,} VND")
                print(f"- Từ thời điểm: {self.qr_start_time.strftime('%d/%m/%Y %H:%M:%S')}")
                
                # Main transaction check loop
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
                                # Break out if stop signal received during processing
                                if self.stop_transaction_check.is_set():
                                    break
                                    
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
                                        print(f"Phát hiện giao dịch ({current_time.strftime('%H:%M:%S')})")
                                        print(f"Thời gian GD: {trans_time.strftime('%d/%m/%Y %H:%M:%S')}")
                                        print(f"Số tiền nhận: +{credit:,} VND")
                                        print(f"Từ: {trans.get('benAccountName', 'N/A')}")
                                        print(f"Nội dung: {description}")
                                        print(f"Mã GD: {trans_id}")
                                        print("="*50)
                                        
                                        # Store the donation amount for success page
                                        QRCodePage.donation_amount = credit
                                        
                                        # Store the transfer content for the note field
                                        QRCodePage.transfer_content = description
                                        
                                        # Đóng kết nối trước khi emit signal
                                        if mb:
                                            try:
                                                # Sử dụng _req.close() khi có _req
                                                if hasattr(mb, '_req') and mb._req is not None and hasattr(mb._req, 'close'):
                                                    mb._req.close()
                                                mb = None
                                            except Exception as close_e:
                                                print(f"Warning during connection cleanup: {close_e}")
                                        
                                        # Emit signal to switch to success page
                                        self.switch_to_success.emit()
                                        return
                                        
                                except Exception as e:
                                    print(f"Error processing transaction: {e}")
                                    continue
                        
                        # Break loop into small chunks with regular checks for stop signal
                        for _ in range(int(check_interval * 5)):  # 5 checks per second
                            if self.stop_transaction_check.is_set():
                                break
                            time.sleep(0.2)
                        
                    except Exception as e:
                        print(f"Error checking transactions: {e}")
                        check_retry_count += 1
                        
                        # If too many check errors, try to reconnect
                        if check_retry_count >= max_check_retries:
                            print(f"Maximum check retries ({max_check_retries}) reached, stopping check")
                            return
                        
                        # Wait a bit longer after errors (with chunked sleep)
                        for _ in range(5):  # 1 second in small chunks
                            if self.stop_transaction_check.is_set():
                                break
                            time.sleep(0.2)
            else:
                print("Authentication failed - fallback timer will handle transition")
                
        except Exception as e:
            print(f"Lỗi ngoài quá trình check transaction: {str(e)}")
        finally:
            # Đảm bảo dọn dẹp tài nguyên khi kết thúc
            if mb:
                try:
                    print("Đang đăng xuất và đóng kết nối...")
                    # Kiểm tra mb._req có tồn tại không và có phương thức close không
                    if hasattr(mb, '_req') and mb._req is not None and hasattr(mb._req, 'close'):
                        mb._req.close()
                    mb = None
                except Exception as close_e:
                    print(f"Warning during logout: {close_e}")
            
            # Đảm bảo giải phóng tài nguyên
            print("Cleaning up transaction check thread resources")
            gc.collect()

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
                sound_path_payment = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sound', 'payment-success.wav'))
                
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
                        
                        # Wait for payment sound then show success page
                        QTimer.singleShot(2500, lambda: self.transition_overlay.fadeIn(show_new_page))
                    
                    # Start the sequence
                    self.ting_sound.play()
                    QTimer.singleShot(1000, play_payment_and_speak)
                    
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
        
        # Nếu target_time chưa được đặt, đặt nó bây giờ
        if not hasattr(self, 'target_time') or self.target_time is None:
            self.target_time = current_time + timedelta(seconds=self.countdown_seconds)
            
        # Tính thời gian còn lại
        remaining = (self.target_time - current_time).total_seconds()
        
        if remaining <= 0:
            self.countdown_timer.stop()
            self.countdown_label.setText(_("qrCodePage.qrExpired"))
            
            # When timer expires, chuyển sang chế độ No Banking
            print("Timer expired - proceeding with No Banking flow")
            QRCodePage.donation_amount = 0
            self.stop_transaction_check.set()
            
            # Check if already in transition
            if not hasattr(self, 'transition_in_progress') or not self.transition_in_progress:
                self.transition_in_progress = True
                
                # Thực hiện logic giống như nhấn nút No Banking
                QRCodePage.transfer_content = "Heartfelt support donation"
                
                # Switch to success page with zero donation
                self.switch_to_success.emit()
            return
            
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        self.countdown_label.setText(f"{_('qrCodePage.timeRemaining')}{minutes:02d}:{seconds:02d}")

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
        print("No Banking selected")
        
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
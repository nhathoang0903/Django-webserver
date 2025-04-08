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
import subprocess  # Add this import at the top

from base_page import BasePage 
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                           QFrame, QApplication, QPushButton) 
from mbbank import MBBank 
from PyQt5.QtCore import Qt, QTimer, QDateTime, pyqtSignal, QUrl
from PyQt5.QtGui import QFont, QPixmap, QIcon, QImage, QColor, QBitmap, QFontDatabase
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

class QRCodePage(BasePage):  # Changed from QWidget to BasePage
    switch_to_success = pyqtSignal()  # Signal for page switching
    payment_completed = pyqtSignal(bool)  # Signal for payment status
    
    def __init__(self):
        # Force CPU configuration before any other initialization
        self.configure_device()
        super().__init__()
        
        # Remove pygame sound initialization
        self.sound_enabled = False  # Disable sound functionality
        
        # Rest of initialization
        self.installEventFilter(self)  # Register event filter
        self.page_load_time = time.time()  # Track when page loads
        self.cart_state = CartState()
        # Set application icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))
        # Calculate total first
        raw_total = sum(float(product['price']) * quantity 
                       for product, quantity in self.cart_state.cart_items)
        self.total_amount = int(raw_total)
        
        # Check if total is zero
        if self.total_amount == 0:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Invalid total amount")
            msg.setInformativeText("Cannot generate QR code for zero amount.")
            msg.setWindowTitle("Error")
            msg.exec_()
            self.close()
            return
            
        # pygame.mixer.init()  # Initialize pygame for sound
        self.qr_start_time = None  # Add start time tracking
        self.processed_transaction_ids = set()  # Thêm set để lưu các ID đã xử lý
        
        # Calculate and format total amount properly
        raw_total = sum(float(product['price']) * quantity 
                       for product, quantity in self.cart_state.cart_items)
        self.total_amount = int(raw_total)  # Convert to integer to avoid floating point issues
        print(f"Initialized total amount: {self.total_amount}")  # Debug print
        
        self.init_ui()
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_seconds = 300  # 5 minutes
        self.target_time = datetime.now()  # Set target time when page opens
        self.load_qr_code()
        # Start transaction check after QR is loaded
        self.stop_transaction_check = Event()  # Add event to stop transaction check
        self.start_transaction_check()
        self.switch_to_success.connect(self.handle_success)  # Connect signal to handler
        self.shopping_page = None  # Add reference to shopping page
        self.transition_overlay = PageTransitionOverlay(self)  # Add transition overlay

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
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))

    def init_ui(self):
        self.setWindowTitle('QR Code Payment')
        # Remove setGeometry and setFixedSize since handled by BasePage
        self.setStyleSheet("background-color: #F5F9F7;")

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
        self.setWindowIcon(QIcon(icon_path))

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Left Section with centered content
        left_section = QWidget()
        left_layout = QVBoxLayout(left_section)
        left_layout.setContentsMargins(20, 20, 20, 20)

        # Logo at top
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(154, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        left_layout.addWidget(logo_label)

        # Add stretch before text
        left_layout.addStretch(1)

        # Center text section
        title_label = QLabel("PayNow QR Code")
        title_label.setFont(QFont("Inria Sans", 17))
        title_label.setStyleSheet("color: black;")
        left_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        instruction_label = QLabel("Scan or upload this QR code to your Banking app")
        instruction_label.setFont(QFont("Inria Sans", 10, QFont.Light, italic=True))
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setStyleSheet("color: black;")
        left_layout.addWidget(instruction_label, alignment=Qt.AlignCenter)

        # Add Cancel Payment button below title and instruction labels
        self.cancel_button = QPushButton("Cancel Payment")
        self.cancel_button.setFont(QFont("Inter", 11, QFont.Bold))
        self.cancel_button.setFixedSize(200, 50)
        self.cancel_button.setStyleSheet("""
        background-color: #507849;
        color: white;
        border-radius:15px;
        """)
        self.cancel_button.clicked.connect(self.cancel_payment)
        left_layout.addWidget(self.cancel_button, alignment=Qt.AlignCenter)

        # Add stretch after text
        left_layout.addStretch(1)

        left_layout.addStretch()
        main_layout.addWidget(left_section)

        # Right Section
        right_section = QWidget()
        right_layout = QVBoxLayout(right_section)
        right_layout.setContentsMargins(20, 0, 20, 20)  # Set top margin to 0
        right_layout.setSpacing(15)
        right_layout.setAlignment(Qt.AlignTop)  # Force alignment to top

        # QR Code Frame
        self.qr_frame = QFrame()
        self.qr_frame.setFixedSize(300, 300)  # Reduced from 350x350 to 300x300
        self.qr_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F9F7;
                border: none;
                margin-top: 20px;  /* Add top margin */
            }
        """)
        
        # QR Code Label
        self.qr_label = QLabel(self.qr_frame)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setFixedSize(300, 300)  # Reduced from 350x350 to 300x300
        self.qr_label.setText("Loading...")
        self.qr_label.setStyleSheet("background-color: transparent;")

        # Payment Details Container
        details_frame = QFrame()
        details_frame.setStyleSheet("background-color: transparent;")
        details_layout = QVBoxLayout(details_frame)
        details_layout.setSpacing(8)

        # Amount
        self.amount_label = QLabel()
        self.amount_label.setFont(QFont("Inria Sans", 11))
        amount_text = sum(float(product['price']) * quantity 
                         for product, quantity in self.cart_state.cart_items)
        self.amount_label.setText(f"Số tiền: {'{:,.0f}'.format(amount_text).replace(',', '.')} vnđ")

        # Account Details
        acc_name_label = QLabel("Tên chủ tài khoản: NGUYEN THE NGO")
        acc_name_label.setFont(QFont("Inria Sans", 11))
        
        bank_label = QLabel("Ngân hàng: TMCP Quân Đội")
        bank_label.setFont(QFont("Inria Sans", 11))

        # Add all labels to details layout
        for label in [self.amount_label, acc_name_label, bank_label]:
            label.setAlignment(Qt.AlignCenter)
            details_layout.addWidget(label)

        # Countdown label
        self.countdown_label = QLabel()
        self.countdown_label.setFont(QFont("Inria Sans", 12, QFont.Bold))
        self.countdown_label.setStyleSheet("color: #D30E11;")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.hide()

        # Generation time label
        self.gen_time_label = QLabel()
        self.gen_time_label.setFont(QFont("Inria Sans", 12, italic=True))
        self.gen_time_label.setAlignment(Qt.AlignCenter)
        self.gen_time_label.hide()

        # Add widgets in desired order with adjusted spacing
        right_layout.addWidget(self.qr_frame, alignment=Qt.AlignTop | Qt.AlignHCenter)
        right_layout.addStretch(1)  # Add stretch to push details down
        right_layout.addWidget(details_frame)
        right_layout.addSpacing(10)  # Small spacing between details and countdown
        right_layout.addWidget(self.countdown_label, alignment=Qt.AlignCenter)
        right_layout.addWidget(self.gen_time_label, alignment=Qt.AlignCenter)
        
        # Remove the stretch to prevent pushing content to center
        # right_layout.addStretch()

        main_layout.addWidget(right_section)

    def load_qr_code(self):
        try:
            # Set the start time when QR is generated
            self.qr_start_time = datetime.now()
            
            # Debug prints to verify amount
            print(f"Generating QR for amount: {self.total_amount}")
            
            # VietQR configuration
            bank_name = "MB"  # MB Bank
            account_number = "0375712517"  #account number 
            bank_code = getBincode(bank_name)
            print(f"Bank code: {bank_code}")  # Debug print

            # Generate VietQR string with proper format
            vietqr_string = genQRString(
                merchant_id=account_number,
                acq=bank_code,
                amount=str(self.total_amount),  # Convert amount to string
                merchant_name="NGUYEN THE NGO",  # Add merchant name
                service_code="QRIBFTTA"  
            )
            
            # Print out generated string for debugging
            print(f"Generated VietQR string: {vietqr_string}")

            # Create QR code with custom styling
            qr = qrcode.QRCode(
                version=5,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=12,  # Increased box size for better scanning
                border=4
            )
            
            qr.add_data(vietqr_string)
            qr.make(fit=True)
            
            # Create QR image with custom colors
            qr_img = qr.make_image(fill_color="#2C7A7B", back_color="#F5F9F7").convert("RGBA")
            
            # Convert PIL Image to QPixmap using BytesIO
            img_byte_array = io.BytesIO()
            qr_img.save(img_byte_array, format='PNG')
            img_byte_array.seek(0)  # Reset buffer position
            
            # Create QPixmap from bytes
            qr_pixmap = QPixmap()
            qr_pixmap.loadFromData(img_byte_array.getvalue())
            
            # Display QR code with proper scaling and position
            self.qr_label.setPixmap(qr_pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.qr_label.setAlignment(Qt.AlignCenter)
            
            # Adjust QR frame position
            self.qr_frame.setFixedSize(300, 300)  
            self.qr_frame.setStyleSheet("""
                QFrame {
                    background-color: #F5F9F7;
                    border: none;
                    margin-top: 20px;  
                }
            """)
            
            # Show generation time with ordinal suffix
            current_time = QDateTime.currentDateTime()
            day = current_time.date().day()
            
            # Get ordinal suffix
            if day in [1, 21, 31]:
                suffix = "st"
            elif day in [2, 22]:
                suffix = "nd"
            elif day in [3, 23]:
                suffix = "rd"
            else:
                suffix = "th"

            # Format date with superscript suffix
            date_str = f"{day}<sup>{suffix}</sup>"
            time_str = current_time.toString('hh:mm:ss')
            month_str = current_time.toString('MMM')
            year_str = current_time.toString('yyyy')
            
            self.gen_time_label.setText(
                f"Generated {time_str}, {month_str} {date_str}, {year_str}")
            self.gen_time_label.setTextFormat(Qt.RichText)  # Enable HTML formatting
            self.gen_time_label.show()
            print("QR code generated at:", current_time.toString('hh:mm:ss, MMM d, yyyy'))
            
            # Start countdown
            self.countdown_timer.start(1000)
            self.countdown_label.show()
            
            # Start transaction check with proper thread management
            self.start_transaction_check()
            
        except Exception as e:
            print(f"Error loading QR code: {e}")
            self.qr_label.setText("Failed to load QR Code")
            # Ensure cleanup happens even if QR fails
            self.cleanup_resources()
            # Return to shopping page after 2 seconds on failure
            QTimer.singleShot(2000, self.return_to_shopping)

    def cancel_payment(self):
        """Handle cancel payment action"""
        self.stop_transaction_check.set()  # Signal to stop transaction check
        self.countdown_timer.stop()
        self.return_to_shopping()
        
    def return_to_shopping(self):
        """Return to shopping page when QR expires or payment is canceled"""
        transition_start = time.time()
        
        from page4_shopping import ShoppingPage
        self.shopping_page = ShoppingPage()
        
        # Calculate transition time
        transition_time = time.time() - transition_start
        print(f"Time to return to shopping: {transition_time:.2f} seconds")
        
        self.shopping_page.show()
        self.cleanup_resources()
        self.close()

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
        try:
            print("Khởi tạo kết nối...")
            mb = MBBank(username=USERNAME, password=PASSWORD)
            
            print("Đang đăng nhập...")
            mb._authenticate()
            print("Xác thực thành công!")
            
            print(f"\nBat dau theo doi giao dịch:")
            print(f"- Số tiền: {amount:,} VND")
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
                                
                                # Check conditions:
                                # 1. Is credit transaction (credit > 0, debit = 0)
                                # 2. Amount matches QR code
                                # 3. Transaction time after QR creation
                                # 4. Transaction not processed before
                                if (credit == amount and debit == 0 and
                                    trans_time > self.qr_start_time and
                                    trans_id not in self.processed_transaction_ids):
                                    
                                    self.processed_transaction_ids.add(trans_id)
                                    print("\n" + "="*50)
                                    print(f"Phat hien giao dich khop ({current_time.strftime('%H:%M:%S')})")
                                    print(f"Thoi gian GD: {trans_time.strftime('%d/%m/%Y %H:%M:%S')}")
                                    print(f"So tien nhan: +{credit:,} VND")
                                    print(f"Tu: {trans.get('benAccountName', 'N/A')}")
                                    print(f"Noi dung: {trans.get('description', 'N/A')}")
                                    print(f"Ma GD: {trans_id}")
                                    print("="*50)
                                    
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
                            # Lấy số tiền trực tiếp từ total_amount
                            amount = self.total_amount
                            amount_words = self.number_to_vietnamese(amount)
                            print(f"Speaking amount: {amount} ({amount_words})")  # Debug print
                            
                            # Chỉ đọc số tiền với tốc độ chậm hơn (100 từ/phút)
                            subprocess.run(['espeak', '-vvi', '-s100', '-g5', amount_words + ' đồng'])
                        except Exception as e:
                            print(f"Error speaking amount: {e}")
                    
                    # Tăng delay lên 2500ms để đảm bảo âm thanh sucesspayment.wav phát xong
                    QTimer.singleShot(2500, speak_amount)
                
                # Start the sequence
                self.ting_sound.play()
                QTimer.singleShot(1000, play_payment_and_speak)
                
            except Exception as e:
                print(f"Error playing sounds: {e}")
                
            # Tăng delay chuyển trang lên 7000ms để đảm bảo tất cả âm thanh phát xong
            QTimer.singleShot(7000, lambda: self.transition_overlay.fadeIn(show_new_page))
            
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
            self.countdown_label.setText("QR Code expired")
            self.return_to_shopping()
            return
            
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        self.countdown_label.setText(f"Time remaining: {minutes:02d}:{seconds:02d}")

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

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = QRCodePage()
    window.show()
    sys.exit(app.exec_())
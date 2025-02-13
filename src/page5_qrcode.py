from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                           QFrame, QApplication)
from PyQt5.QtCore import Qt, QTimer, QDateTime, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QIcon, QImage, QColor, QBitmap, QFontDatabase
import os
import requests
import cv2
import numpy as np
from io import BytesIO
import pygame
from datetime import datetime
import time
import json
from PIL import Image
from cart_state import CartState
from threading import Thread

class QRCodePage(QWidget):
    switch_to_success = pyqtSignal()  # Add signal for page switching
    
    def __init__(self):
        super().__init__()
        self.cart_state = CartState()
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
            
        pygame.mixer.init()  # Initialize pygame for sound
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
        self.start_transaction_check()
        self.switch_to_success.connect(self.handle_success)  # Connect signal to handler

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
        self.setGeometry(100, 100, 800, 480)
        self.setFixedSize(800, 480)
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

        # Add stretch after text
        left_layout.addStretch(1)

        left_layout.addStretch()
        main_layout.addWidget(left_section)

        # Right Section
        right_section = QWidget()
        right_layout = QVBoxLayout(right_section)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        # QR Code Frame
        self.qr_frame = QFrame()
        self.qr_frame.setFixedSize(259, 376)
        self.qr_frame.setStyleSheet("background-color: transparent;")
        
        # QR Code Label
        self.qr_label = QLabel(self.qr_frame)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setFixedSize(259, 376)
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
        # acc_name_label = QLabel("Tên chủ tài khoản: VO PHAN NHAT HOANG")
        # acc_num_label = QLabel("Số tài khoản: 3099932002")
        # bank_label = QLabel("Ngân hàng TMCP Quân Đội")

        # for label in [self.amount_label, acc_name_label, acc_num_label, bank_label]:
        #     label.setFont(QFont("Inter", 11))
        #     details_layout.addWidget(label)

        # Countdown label
        self.countdown_label = QLabel()
        self.countdown_label.setFont(QFont("Inria Sans", 10))
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.hide()

        # Generation time label
        self.gen_time_label = QLabel()
        self.gen_time_label.setFont(QFont("Inria Sans", 12, italic=True))
        self.gen_time_label.setAlignment(Qt.AlignCenter)
        self.gen_time_label.hide()

        # Add widgets in desired order
        right_layout.addWidget(self.qr_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)
        right_layout.addWidget(details_frame)
        right_layout.addWidget(self.countdown_label, alignment=Qt.AlignCenter)
        right_layout.addWidget(self.gen_time_label, alignment=Qt.AlignCenter)
        right_layout.addStretch()

        main_layout.addWidget(right_section)

    def load_qr_code(self):
        try:
            # Set the start time when QR is generated
            self.qr_start_time = datetime.now()
            
            # Debug prints to verify amount
            print(f"Generating QR for amount: {self.total_amount}")
            print(f"URL amount parameter: {self.total_amount}")
            
            url = (f"https://img.vietqr.io/image/mbbank-3099932002-print.jpg?"
                  f"amount={self.total_amount}&accountName=VO%20PHAN%20NHAT%20HOANG")
            print(url)
            print("Creating QR code for total amount:", self.total_amount)
            
            response = requests.get(url)
            image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
            # Read as BGR image
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            # Create mask for white pixels
            lower_white = np.array([250, 250, 250])
            upper_white = np.array([255, 255, 255])
            mask = cv2.inRange(image, lower_white, upper_white)
            
            # Create transparent image with alpha channel
            rgba = cv2.cvtColor(image, cv2.COLOR_BGR2RGBA)
            # Set alpha channel to 0 for white pixels
            rgba[mask == 255] = [0, 0, 0, 0]
            
            # Convert to RGB for display
            h, w, ch = rgba.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgba.data, w, h, bytes_per_line, QImage.Format_RGBA8888)
            qr_pixmap = QPixmap.fromImage(qt_image)
            
            self.qr_label.setPixmap(qr_pixmap.scaled(300, 400, Qt.KeepAspectRatio))
            
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
            
        except Exception as e:
            self.qr_label.setText("Failed to load QR Code")
            print(f"Error loading QR code: {e}")

    def update_countdown(self):
        if self.countdown_seconds > 0:
            minutes = self.countdown_seconds // 60
            seconds = self.countdown_seconds % 60
            self.countdown_label.setText(f"QR code expires in {minutes:02d}:{seconds:02d}")
            self.countdown_label.setStyleSheet("color: #D30E11;")
            self.countdown_seconds -= 1
        else:
            self.countdown_timer.stop()
            self.countdown_label.setText("Expired")

    def start_transaction_check(self):
        check_thread = Thread(
            target=self.check_transaction,
            args=(self.total_amount,),  # Pass the integer amount
            daemon=True
        )
        check_thread.start()

    def check_transaction(self, amount):
        API_TOKEN = 'XUWZS8RM4UB3WAJRPUBNZDSXYTJJQMBRVP6NRE37XZUKAGL2G6IW9SAFPCGFWIHL'
        CHECK_TRANSACTION_URL = 'https://my.sepay.vn/userapi/transactions/list'
        ting_sound_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        'sound', 'ting-ting.mp3')
        success_sound_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        'sound', 'payment-success.mp3')

        headers = {
            'Authorization': f'Bearer {API_TOKEN}',
            'Content-Type': 'application/json'
        }

        print(f"Starting transaction check. QR generated at: {self.qr_start_time}")
        print(f"Checking for amount: {amount} VND")

        while True:
            try:
                response = requests.get(CHECK_TRANSACTION_URL, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data['status'] == 200 and data['messages']['success']:
                        transactions = data['transactions']
                        if transactions:
                            latest_transaction = transactions[0]
                            transaction_id = latest_transaction['id']
                            latest_amount_in = int(float(latest_transaction['amount_in']))
                            
                            transaction_time_str = latest_transaction['transaction_date']
                            transaction_time = datetime.strptime(transaction_time_str, '%Y-%m-%d %H:%M:%S')
                            
                            # Tính thời gian chênh lệch
                            time_diff = abs((transaction_time - self.qr_start_time).total_seconds())
                            
                            print(f"Transaction ID: {transaction_id}")
                            print(f"Time difference: {time_diff} seconds")
                            
                            # Kiểm tra điều kiện:
                            # 1. Số tiền khớp
                            # 2. Thời gian giao dịch trong vòng 5 phút của thời điểm tạo QR
                            # 3. Giao dịch chưa được xử lý trước đó
                            if (latest_amount_in == amount and 
                                time_diff <= 300 and  # 5 phút = 300 giây
                                transaction_id not in self.processed_transaction_ids):
                                
                                self.processed_transaction_ids.add(transaction_id)
                                print("✓ Transaction successful!")
                                
                                # Phát âm thanh theo thứ tự
                                pygame.mixer.music.load(ting_sound_file)
                                pygame.mixer.music.play()
                                pygame.time.wait(1000)
                                
                                pygame.mixer.music.load(success_sound_file)
                                pygame.mixer.music.play()
                                pygame.time.wait(1000)
                                
                                # Emit signal instead of directly switching pages
                                self.switch_to_success.emit()
                                break

                time.sleep(0.2)
                
            except Exception as e:
                print(f"Error checking transaction: {e}")
                time.sleep(0.2)

    def handle_success(self):
        """Handle successful transaction in main thread"""
        self.countdown_timer.stop()
        # Don't clear cart here anymore - let page6 handle it
        from page6_success import SuccessPage
        self.success_page = SuccessPage()
        self.success_page.show()
        self.close()

    def closeEvent(self, event):
        self.countdown_timer.stop()
        event.accept()

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = QRCodePage()
    window.show()
    sys.exit(app.exec_())

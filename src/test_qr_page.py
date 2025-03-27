from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                           QFrame, QApplication)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont, QPixmap
import qrcode
from vietqr.VietQR import genQRString, getBincode
from PIL import Image
import io
from datetime import datetime

class TestQRPage(QWidget):
    def __init__(self):
        super().__init__()
        self.total_amount = 2000  # Fixed test amount
        
        # Add countdown timer
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_seconds = 300  # 5 minutes
        
        self.init_ui()
        self.load_qr_code()

    def init_ui(self):
        self.setWindowTitle('QR Code Test')
        self.setStyleSheet("background-color: #F5F9F7;")
        self.setFixedSize(800, 480)

        # Main layout
        main_layout = QHBoxLayout(self)
        
        # Right section for QR and details
        right_section = QWidget()
        right_layout = QVBoxLayout(right_section)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        # QR Frame
        self.qr_frame = QFrame()
        self.qr_frame.setFixedSize(259, 376)
        self.qr_frame.setStyleSheet("background-color: transparent;")
        
        # QR Label
        self.qr_label = QLabel(self.qr_frame)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setFixedSize(259, 376)
        self.qr_label.setStyleSheet("background-color: transparent;")

        # Bank details container
        details_frame = QFrame()
        details_frame.setStyleSheet("background-color: transparent;")
        details_layout = QVBoxLayout(details_frame)
        details_layout.setSpacing(8)

        # Bank Details Labels
        bank_details = [
            ("Ngân hàng TMCP Quân đội", "bank_name"),
            ("Tên tài khoản: NGUYEN THE NGO", "acc_name"),
            (f"Số tiền: {'{:,.0f}'.format(self.total_amount).replace(',', '.')} vnđ", "amount")
        ]

        for text, name in bank_details:
            label = QLabel(text)
            label.setFont(QFont("Inria Sans", 12))
            label.setStyleSheet("color: black;")
            details_layout.addWidget(label)

        # Add countdown label
        self.countdown_label = QLabel()
        self.countdown_label.setFont(QFont("Inria Sans", 10))
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet("color: #D30E11;")

        # Add generation time label
        self.gen_time_label = QLabel()
        self.gen_time_label.setFont(QFont("Inria Sans", 12, italic=True))
        self.gen_time_label.setAlignment(Qt.AlignCenter)

        # Add widgets to layout
        right_layout.addWidget(self.qr_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)
        right_layout.addWidget(details_frame)
        right_layout.addWidget(self.countdown_label, alignment=Qt.AlignCenter)
        right_layout.addWidget(self.gen_time_label, alignment=Qt.AlignCenter)
        right_layout.addStretch()

        main_layout.addWidget(right_section)

    def load_qr_code(self):
        try:
            # VietQR configuration
            bank_name = "MB"
            account_number = "0375712517"
            bank_code = getBincode(bank_name)
            
            # Generate VietQR string
            vietqr_string = genQRString(
                merchant_id=account_number,
                acq=bank_code,
                amount=str(self.total_amount),
                merchant_name="NGUYEN THE NGO",
                service_code="QRIBFTTA"
            )
            
            # Create QR code
            qr = qrcode.QRCode(
                version=5,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4
            )
            
            qr.add_data(vietqr_string)
            qr.make(fit=True)
            
            # Create QR image with background matching page color
            qr_img = qr.make_image(fill_color="#507849", back_color="#F5F9F7")
            
            # Add border and styling
            qr_img = qr_img.convert("RGBA")
            border_size = 30
            new_size = (qr_img.size[0] + border_size, qr_img.size[1] + border_size)
            canvas = Image.new("RGBA", new_size, "#F5F9F7")
            canvas.paste(qr_img, (border_size // 2, border_size // 2), qr_img)
            
            # Convert to QPixmap
            img_byte_array = io.BytesIO()
            canvas.save(img_byte_array, format='PNG')
            qr_pixmap = QPixmap()
            qr_pixmap.loadFromData(img_byte_array.getvalue())
            
            # Display QR code
            self.qr_label.setPixmap(qr_pixmap.scaled(300, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
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
            self.gen_time_label.setTextFormat(Qt.RichText)
            
            # Start countdown
            self.countdown_timer.start(1000)
            
        except Exception as e:
            self.qr_label.setText("Failed to load QR Code")
            print(f"Error loading QR code: {e}")

    def update_countdown(self):
        if self.countdown_seconds > 0:
            minutes = self.countdown_seconds // 60
            seconds = self.countdown_seconds % 60
            self.countdown_label.setText(f"QR code expires in {minutes:02d}:{seconds:02d}")
            self.countdown_seconds -= 1
        else:
            self.countdown_timer.stop()
            self.countdown_label.setText("Expired")

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = TestQRPage()
    window.show()
    sys.exit(app.exec_())
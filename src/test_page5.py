import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QDateTime
from page5_qrcode import QRCodePage
from cart_state import CartState
from datetime import datetime

class TestQRPage(QRCodePage):
    def __init__(self):
        super().__init__()
        
        # Initialize required attributes
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_seconds = 300  # 5 minutes
        self.target_time = datetime.now()
        
        # Set a fixed test amount
        self.total_amount = 250000  # 250,000 VND
        
        # Create test cart items
        test_cart_items = [
            ({"name": "Test Product 1", "price": "150000"}, 1),
            ({"name": "Test Product 2", "price": "100000"}, 1),
        ]
        
        # Set cart state
        self.cart_state.cart_items = test_cart_items
        
        # Initialize UI and load QR
        self.init_ui()
        self.load_qr_code()

def main():
    app = QApplication(sys.argv)
    window = TestQRPage()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 
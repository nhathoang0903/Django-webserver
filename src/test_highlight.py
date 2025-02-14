
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import QTimer
import sys
import os

# Thêm thư mục cha vào path để import được các module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.cart_item_widget import CartItemWidget

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setGeometry(100, 100, 400, 150)
        self.setWindowTitle('Test Highlight Animation')
        
        layout = QVBoxLayout()
        
        # Tạo một product giả để test
        test_product = {
            'name': 'Test Product',
            'price': '10000',
            'category': 'Đồ ăn vặt',
            'image_url': 'https://pvmarthanoi.com.vn/wp-content/uploads/2023/02/mi-handy-hao-hao-tom-chua-cay-ly-67g-201912051400437161.jfif_-500x600.png'  # URL ảnh giả
        }
        
        # Tạo cart item widget với product test
        self.cart_item = CartItemWidget(test_product, 1)
        layout.addWidget(self.cart_item)
        
        self.setLayout(layout)
        
        # Tự động highlight sau 1 giây
        QTimer.singleShot(1000, self.cart_item.highlight)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
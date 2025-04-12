from cart_state import CartState
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from cart_utils import add_cart_count_label

class ProductPage(QWidget):
    def __init__(self):
        super().__init__()
        self.cart_state = CartState()  # Sử dụng cùng instance của CartState
        
        # Thiết lập layout cho widget
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        
        # Thêm widget "Your Cart"
        add_cart_count_label(self)
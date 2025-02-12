
from cart_state import CartState
from PyQt5.QtWidgets import QWidget

class ProductPage(QWidget):
    def __init__(self):
        super().__init__()
        self.cart_state = CartState()  # Sử dụng cùng instance của CartState
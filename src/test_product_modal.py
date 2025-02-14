from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt
from product_modal import ProductModal
import sys

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Test Product Modal')
        self.setGeometry(100, 100, 800, 480)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create test buttons
        self.create_test_buttons(layout)
        
        # Initialize modal
        self.product_modal = ProductModal(self)
        self.product_modal.add_to_cart.connect(self.on_add_to_cart)
        self.product_modal.cancel_clicked.connect(self.on_cancel)
        self.product_modal.hide()

    def create_test_buttons(self, layout):
        # Test case 1: New product
        test_btn1 = QPushButton('Test New Product')
        test_btn1.clicked.connect(self.show_new_product)
        layout.addWidget(test_btn1)

        # Test case 2: Existing product
        test_btn2 = QPushButton('Test Existing Product')
        test_btn2.clicked.connect(self.show_existing_product)
        layout.addWidget(test_btn2)

        # Test case 3: Long name product
        test_btn3 = QPushButton('Test Long Name Product')
        test_btn3.clicked.connect(self.show_long_name_product)
        layout.addWidget(test_btn3)

        # Add more test cases as needed
        layout.addStretch()

    def show_new_product(self):
        test_product = {
            'name': 'Pepsi',
            'price': '15000',
            'category': 'Thức uống',  # Add category to trigger 75x140 size
            'image_url': 'https://cdn.tgdd.vn/Products/Images/2563/200778/bhx/nuoc-uong-good-mood-vi-sua-chua-455ml-202407111335443811.jpg'
        }
        self.show_modal(test_product)

    def show_existing_product(self):
        test_product = {
            'name': 'Pepsi',
            'price': '15000',
            'category': 'Thức uống',  # Add category to trigger 75x140 size
            'image_url': 'https://pvmarthanoi.com.vn/wp-content/uploads/2023/02/mi-handy-hao-hao-tom-chua-cay-ly-67g-201912051400437161.jfif_-500x600.png'
        }
        self.show_modal(test_product, existing_quantity=2)

    def show_long_name_product(self):
        test_product = {
            'name': 'Long name Long name Long name Long name',
            'price': '15000',
            'category': 'Thức uống',  # Add category to trigger 75x140 size
            'image_url': 'https://cdn.tgdd.vn/Products/Images/2563/200778/bhx/nuoc-uong-good-mood-vi-sua-chua-455ml-202407111335443811.jpg'
        }
        self.show_modal(test_product)

    def show_modal(self, product, existing_quantity=None):
        # Position modal in center of window
        modal_x = (self.width() - self.product_modal.width()) // 2
        modal_y = (self.height() - self.product_modal.height()) // 2
        self.product_modal.move(modal_x, modal_y)
        
        # Update and show modal
        self.product_modal.update_product(product, existing_quantity)
        self.product_modal.show()
        self.product_modal.raise_()

    def on_add_to_cart(self, product, quantity):
        print(f"Added to cart: {product['name']}, Quantity: {quantity}")
        self.product_modal.hide()

    def on_cancel(self):
        print("Modal cancelled")
        self.product_modal.hide()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
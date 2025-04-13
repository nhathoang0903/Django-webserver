import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt
from product_modal import ProductModal

class TestProductModal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Product Modal Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create buttons to show different product types
        buttons_layout = QHBoxLayout()
        
        # Button for regular product
        regular_btn = QPushButton("Show Regular Product")
        regular_btn.clicked.connect(lambda: self.show_product("regular"))
        buttons_layout.addWidget(regular_btn)
        
        # Button for snack product
        snack_btn = QPushButton("Show Snack Product")
        snack_btn.clicked.connect(lambda: self.show_product("snack"))
        buttons_layout.addWidget(snack_btn)
        
        # Button for beverage product
        beverage_btn = QPushButton("Show Beverage Product")
        beverage_btn.clicked.connect(lambda: self.show_product("beverage"))
        buttons_layout.addWidget(beverage_btn)
        
        # Button for food product
        food_btn = QPushButton("Show Food Product")
        food_btn.clicked.connect(lambda: self.show_product("food"))
        buttons_layout.addWidget(food_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # Create a container for the modal
        self.modal_container = QWidget()
        self.modal_container.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        self.modal_container.setFixedSize(350, 300)
        
        # Create layout for the modal container with center alignment
        modal_layout = QVBoxLayout(self.modal_container)
        modal_layout.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.modal_container)
        
        # Initialize product modal
        self.product_modal = None
        
        # Sample product data
        self.sample_products = {
            "regular": {
                "name": "Regular_Product",
                "price": "150000",
                "category": "Other",
                "image_url": os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'default-product.png')
            },
            "snack": {
                "name": "Snack_Product",
                "price": "25000",
                "category": "Đồ ăn vặt",
                "image_url": os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'default-product.png')
            },
            "beverage": {
                "name": "Beverage_Product",
                "price": "35000",
                "category": "Thức uống",
                "image_url": os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'default-product.png')
            },
            "food": {
                "name": "Food_Product",
                "price": "75000",
                "category": "Thức ăn",
                "image_url": os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'default-product.png')
            }
        }
    
    def show_product(self, product_type):
        # Remove previous modal if exists
        if self.product_modal:
            self.product_modal.deleteLater()
        
        # Create new modal
        self.product_modal = ProductModal()
        
        # Get sample product data
        product = self.sample_products[product_type]
        
        # Update modal with product data
        self.product_modal.update_product(product)
        
        # Add modal to container
        layout = self.modal_container.layout()
        layout.addWidget(self.product_modal)
        
        # Show modal
        self.product_modal.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestProductModal()
    window.show()
    sys.exit(app.exec_()) 
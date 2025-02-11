from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
import os

class ProductModal(QFrame):
    add_to_cart = pyqtSignal(dict, int)  # Emits product data and quantity

    def __init__(self, parent=None):
        super().__init__(parent)
        self.quantity = 1
        self.current_product = None
        self.init_ui()
        
    def init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1.5px solid #000000;
                border-radius: 9px;
            }
        """)
        
        layout = QVBoxLayout(self)  # Change to vertical layout
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Product image at top
        self.image_label = QLabel()
        self.image_label.setFixedSize(120, 120)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)
        
        # Product name
        self.name_label = QLabel()
        self.name_label.setFont(QFont("Inter", 12, QFont.Bold))
        self.name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.name_label)
        
        # Quantity controls in horizontal layout
        quantity_widget = QWidget()
        quantity_layout = QHBoxLayout(quantity_widget)
        quantity_layout.setContentsMargins(0, 0, 0, 0)
        
        minus_btn = QPushButton("-")
        self.quantity_label = QLabel("1")
        plus_btn = QPushButton("+")
        
        for btn in [minus_btn, plus_btn]:
            btn.setFixedSize(25, 25)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #507849;
                    color: white;
                    border-radius: 12px;
                    font-weight: bold;
                }
            """)
        
        minus_btn.clicked.connect(self.decrease_quantity)
        plus_btn.clicked.connect(self.increase_quantity)
        
        quantity_layout.addStretch()
        quantity_layout.addWidget(minus_btn)
        quantity_layout.addWidget(self.quantity_label)
        quantity_layout.addWidget(plus_btn)
        quantity_layout.addStretch()
        
        layout.addWidget(quantity_widget)
        
        # Price
        self.price_label = QLabel()
        self.price_label.setFont(QFont("Inter", 12))
        self.price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.price_label)
        
        # Add to cart button
        add_btn = QPushButton("Add to Cart")
        add_btn.setFixedHeight(30)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #507849;
                color: white;
                border-radius: 15px;
                font-weight: bold;
            }
        """)
        add_btn.clicked.connect(self.add_item_to_cart)
        layout.addWidget(add_btn)
        
    def update_product(self, product):
        self.current_product = product
        self.quantity = 1
        self.quantity_label.setText(str(self.quantity))
        
        # Update UI elements
        self.name_label.setText(product['name'])
        self.price_label.setText(f"{product['price']} vnđ")
        
        # Load and display image
        pixmap = QPixmap(product['image_url'])
        self.image_label.setPixmap(pixmap.scaled(120, 120, Qt.KeepAspectRatio))
        
    def increase_quantity(self):
        self.quantity += 1
        self.quantity_label.setText(str(self.quantity))
        
    def decrease_quantity(self):
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.setText(str(self.quantity))
            
    def add_item_to_cart(self):
        if self.current_product:
            self.add_to_cart.emit(self.current_product, self.quantity)
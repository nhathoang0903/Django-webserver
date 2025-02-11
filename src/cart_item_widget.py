
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

class CartItemWidget(QWidget):
    def __init__(self, product, quantity):
        super().__init__()
        self.init_ui(product, quantity)
        
    def init_ui(self, product, quantity):
        layout = QHBoxLayout(self)
        
        # Product image
        image_label = QLabel()
        pixmap = QPixmap(product['image_url'])
        image_label.setPixmap(pixmap.scaled(60, 60, Qt.KeepAspectRatio))
        layout.addWidget(image_label)
        
        # Product info
        info_layout = QHBoxLayout()
        name_label = QLabel(product['name'])
        name_label.setFont(QFont("Inter", 10))
        quantity_label = QLabel(f"x{quantity}")
        price_label = QLabel(f"{product['price'] * quantity} vnđ")
        price_label.setFont(QFont("Inter", 10, QFont.Bold))
        
        info_layout.addWidget(name_label)
        info_layout.addStretch()
        info_layout.addWidget(quantity_label)
        info_layout.addWidget(price_label)
        
        layout.addLayout(info_layout)
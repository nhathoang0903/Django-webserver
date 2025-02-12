from PyQt5.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
import os
from urllib.request import urlopen

class CartItemWidget(QFrame):
    def __init__(self, product, quantity, parent=None):
        super().__init__(parent)
        self.setFixedHeight(70)  # Fixed height for each item
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        # Left: Image
        image_label = QLabel()
        image_label.setFixedSize(60, 60)
        try:
            image_data = urlopen(product['image_url']).read()
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
        except:
            # Use placeholder if image loading fails
            image_label.setText("N/A")
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)

        # Middle: Name and Quantity
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(5)

        # Format name
        name_label = QLabel(product['name'].replace('_', ' '))
        name_label.setFont(QFont("Inria Sans", 10))
        name_label.setWordWrap(True)
        middle_layout.addWidget(name_label)

        # Quantity
        quantity_label = QLabel(f"Quantity: {quantity}")
        quantity_label.setFont(QFont("Inria Sans", 9))
        middle_layout.addWidget(quantity_label)

        layout.addWidget(middle_widget, 1)  # 1 is stretch factor

        # Right: Price and Remove button
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Price
        price_str = "{:,.0f}".format(float(product['price'])).replace(',', '.')
        price_label = QLabel(f"{price_str} vnd")
        price_label.setFont(QFont("Inria Sans", 9))
        price_label.setStyleSheet("color: #D32F2F;")
        right_layout.addWidget(price_label, alignment=Qt.AlignRight)

        # Remove button
        remove_btn = QPushButton()
        remove_btn.setFixedSize(24, 24)
        remove_icon = QPixmap(os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                         'assets', 'remove.png'))
        remove_btn.setIcon(QIcon(remove_icon))
        remove_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 12px;
            }
        """)
        right_layout.addWidget(remove_btn, alignment=Qt.AlignRight)

        layout.addWidget(right_widget)

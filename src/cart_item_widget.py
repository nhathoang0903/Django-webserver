from PyQt5.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget, QSizePolicy
from PyQt5.QtGui import QPixmap, QFont, QIcon, QFontDatabase
from PyQt5.QtCore import Qt
import os
from urllib.request import urlopen

class CartItemWidget(QFrame):

    def load_fonts(self):
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Istok_Web/IstokWeb-Regular.ttf'))

    def __init__(self, product, quantity, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)  # Increased height for more vertical space
        
        # Main frame styling
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 12px 5px;  # Increased vertical padding
            }
        """)
        
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)  # Increased top/bottom margins
        layout.setSpacing(10)
        
        # Left: Image
        image_label = QLabel()
        image_label.setFixedSize(60, 60)
        image_label.setStyleSheet("background-color: white;")  # Ensure white background
        try:
            image_data = urlopen(product['image_url']).read()
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
        except:
            image_label.setText("N/A")
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)
        
        # Middle: Name and Quantity
        middle_widget = QWidget()
        middle_widget.setStyleSheet("background-color: white;")  # Ensure white background
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 4, 0, 4)  # Added vertical padding
        middle_layout.setSpacing(8)  # Increased spacing between name and quantity
        
        # Format name
        name_label = QLabel(product['name'].replace('_', ' '))
        name_label.setFont(QFont("Inria Sans", 9, QFont.Bold))
        name_label.setStyleSheet("background-color: white;")  # Ensure white background
        name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # Allow horizontal expansion
        middle_layout.addWidget(name_label)
        
        # Quantity
        quantity_label = QLabel(f"Quantity: {quantity}")
        quantity_label.setFont(QFont("Inria Sans", 9))
        quantity_label.setStyleSheet("background-color: white;")  # Ensure white background
        middle_layout.addWidget(quantity_label)
        
        layout.addWidget(middle_widget, 1)  # 1 is stretch factor
        
        # Right: Price and Remove button
        right_widget = QWidget()
        right_widget.setStyleSheet("background-color: white;")  # Ensure white background
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 4, 0, 4)  # Added vertical padding
        right_layout.setSpacing(8)  # Increased spacing between price and button
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Price
        price_str = "{:,.0f}".format(float(product['price'])).replace(',', '.')
        price_label = QLabel(f"{price_str} vnd")
        price_label.setFont(QFont("Istok Web", 9, QFont.Bold))
        price_label.setStyleSheet("""
            background-color: white;
            color: #D30E11;
        """)  # Combine background and text color
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
                background-color: white;  /* Set white background */
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 12px;
            }
        """)
        right_layout.addWidget(remove_btn, alignment=Qt.AlignRight)
        
        layout.addWidget(right_widget)
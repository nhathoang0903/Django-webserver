from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel, 
                           QPushButton, QWidget, QSizePolicy, QGraphicsOpacityEffect)
from PyQt5.QtGui import QPixmap, QFont, QIcon, QFontDatabase
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QTimer
import os
from urllib.request import urlopen
from rembg import remove
from PIL import Image
from io import BytesIO

class CartItemWidget(QFrame):
    quantityChanged = pyqtSignal(int)  # Signal for quantity changes
    itemRemoved = pyqtSignal()  # New signal for item removal
    
    def load_fonts(self):
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Istok_Web/IstokWeb-Regular.ttf'))

    def __init__(self, product, quantity, parent=None):
        super().__init__(parent)
        self.load_fonts()
        self.quantity = quantity
        self.product = product
        
        # Add instance variables for price
        self.unit_price = float(product['price'])
        self.current_price = self.unit_price * quantity
        
        self.setFixedHeight(100)  # Reduced from 110 to 100
        self.setFixedWidth(350)   # Increased width from 320 to 350
        
        # Main frame styling
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                padding: 5px;
            }
        """)
        
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(15)
        
        # Left: Image
        image_label = QLabel()
        # Set image size based on category (80% of modal sizes)
        category = product.get('category', '')
        if (category == "Đồ ăn vặt"):
            image_size = (37, 96)  # 75*0.5, 120*0.8
        elif (category == "Thức uống"):
            image_size = (37, 112)  # 75*0.5, 140*0.8
        elif (category == "Thức ăn"):
            image_size = (37, 100)  # 75*0.5, 125*0.8
        else:
            image_size = (37, 96)  # Default size (75*0.5, 120*0.8)
            
        image_label.setFixedSize(*image_size)
        image_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        
        try:
            # Tải ảnh từ URL
            image_data = urlopen(product['image_url']).read()
            
            # Chuyển đổi sang PIL Image và remove background
            input_image = Image.open(BytesIO(image_data))
            output_image = remove(input_image)
            
            # Chuyển đổi lại thành QPixmap với transparency
            byte_array = BytesIO()
            output_image.save(byte_array, format='PNG')
            image_bytes = byte_array.getvalue()
            
            pixmap = QPixmap()
            pixmap.loadFromData(image_bytes)
            
            # Scale theo kích thước category
            scaled_pixmap = pixmap.scaled(image_size[0], image_size[1],
                                        Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"Error loading/processing image: {e}")
            image_label.setText("N/A")
        
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)
        
        # Middle: Name and Quantity Controls
        middle_widget = QWidget()
        middle_widget.setStyleSheet("background-color: white;")
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setContentsMargins(5, 0, 0, 0)
        middle_layout.setSpacing(5)  # Reduced from 8
        
        # Product name container with custom text wrapping
        name_container = QWidget()
        name_container.setFixedWidth(170)
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(0)
        
        # Format name with custom line breaks
        raw_name = product['name'].replace('_', ' ')
        words = raw_name.split()
        if len(words) > 2:
            # Join first two words, then add line break and join remaining words
            formatted_name = ' '.join(words[:2]) + '\n' + ' '.join(words[2:])
        else:
            formatted_name = raw_name
            
        name_label = QLabel(formatted_name)
        name_label.setFont(QFont("Inria Sans", 8, QFont.Bold))
        name_label.setWordWrap(True)
        name_label.setFixedWidth(170)
        name_label.setStyleSheet("""
            QLabel {
                color: #000000; 
                background-color: transparent;
                qproperty-alignment: AlignCenter;
                margin: 0px;
                padding: 0px;
                min-height: 32px;
            }
        """)
        
        name_layout.addWidget(name_label)
        middle_layout.addWidget(name_container, 0, Qt.AlignRight)
        middle_layout.addStretch(1)  # Reduced stretch ratio

        # Quantity controls with smaller size
        control_size = 24  # Reduced from 28 to 24

        # Quantity controls with center alignment
        quantity_container = QHBoxLayout()
        quantity_container.addStretch(3)  # Increased stretch to push more right

        quantity_widget = QWidget()
        quantity_layout = QHBoxLayout(quantity_widget)
        quantity_layout.setContentsMargins(0, 0, 0, 0)
        quantity_layout.setSpacing(0)

        # Updated quantity controls style to match product_modal
        
        # Decrease button
        decrease_btn = QPushButton("-")
        decrease_btn.setFixedSize(control_size, control_size)
        decrease_btn.setFont(QFont("Inria Sans", 13, QFont.Bold))
        decrease_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #000000;
                border: 1px solid #000000;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                border-right: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """)
        decrease_btn.clicked.connect(self.decrease_quantity)
        
        # Quantity label with full borders and explicit border-radius: 0
        self.quantity_label = QLabel(str(quantity))
        self.quantity_label.setFixedSize(control_size, control_size)
        self.quantity_label.setFont(QFont("Inria Sans", 13, QFont.Bold))
        self.quantity_label.setStyleSheet("""
            QLabel {
                background-color: white;
                color: #000000;
                border: 1px solid #000000;
                border-radius: 0px;
                font-size: 14px;
                font-weight: bold;
                qproperty-alignment: AlignCenter;
            }
        """)
        
        # Increase button
        increase_btn = QPushButton("+")
        increase_btn.setFixedSize(control_size, control_size)
        increase_btn.setFont(QFont("Inria Sans", 13, QFont.Bold))
        increase_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #000000;
                border: 1px solid #000000;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                border-left: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """)
        increase_btn.clicked.connect(self.increase_quantity)
        
        quantity_layout.addWidget(decrease_btn)
        quantity_layout.addWidget(self.quantity_label)
        quantity_layout.addWidget(increase_btn)
        
        quantity_container.addWidget(quantity_widget)
        quantity_container.addStretch(1)

        # Add spacing before quantity controls to push them down
        middle_layout.addSpacing(3)  # Reduced from 5
        middle_layout.addLayout(quantity_container)
        middle_layout.addSpacing(2)  # Reduced from 3
        
        layout.addWidget(middle_widget, 1)
        
        # Right side: Price and Remove button
        right_widget = QWidget()
        right_widget.setStyleSheet("background-color: white;")
        right_layout = QVBoxLayout(right_widget)  # Changed to QVBoxLayout
        right_layout.setContentsMargins(10, 3, 0, 0)  # Reduced top margin
        right_layout.setSpacing(5)  # Reduced from 8
        
        # Modify price label to show total price
        self.price_label = QLabel()
        self.price_label.setFont(QFont("Istok Web", 9, QFont.Bold))
        self.price_label.setStyleSheet("""
            background-color: white;
            color: #FF0000;
        """)
        self.price_label.setAlignment(Qt.AlignRight)
        self.update_price_display()  # Update initial price display
        right_layout.addWidget(self.price_label)
        
        # Remove button with larger icon but same button size
        remove_btn = QPushButton()
        remove_btn.setFixedSize(30, 30)  # Keep original button size
        remove_icon = QPixmap(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                       'assets', 'remove.png'))
        scaled_icon = remove_icon.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Larger icon
        remove_btn.setIconSize(scaled_icon.size())  # Set icon size independently
        remove_btn.setIcon(QIcon(scaled_icon))
        remove_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 12px;
            }
        """)
        remove_btn.clicked.connect(self.remove_item)
        remove_container = QWidget()
        remove_container.setStyleSheet("background-color: white;")
        remove_layout = QHBoxLayout(remove_container)
        remove_layout.setContentsMargins(0, 0, 0, 0)
        
        remove_layout.addStretch(1)  # Add stretch before remove button
        remove_layout.addWidget(remove_btn)
        remove_layout.addStretch(1)  # Add stretch after remove button
        
        right_layout.addWidget(remove_container)
        
        layout.addWidget(right_widget)
        
        # Setup animation properties - thay đổi phần này
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.slide_animation.finished.connect(self._on_animation_finished)
        
    def update_price_display(self):
        """Update the price display based on current quantity"""
        self.current_price = self.unit_price * self.quantity
        price_str = "{:,.0f}".format(self.current_price).replace(',', '.')
        self.price_label.setText(f"{price_str} vnđ")

    def increase_quantity(self):
        self.quantity += 1
        self.quantity_label.setText(str(self.quantity))
        self.update_price_display()  # Update price when quantity changes
        self.quantityChanged.emit(self.quantity)
        
    def decrease_quantity(self):
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.setText(str(self.quantity))
            self.update_price_display()  # Update price when quantity changes
            self.quantityChanged.emit(self.quantity)
        else:
            self.remove_item()
    
    def remove_item(self):
        # Start slide animation
        current_pos = self.pos()
        end_pos = QPoint(self.width() + 50, current_pos.y())
        
        self.slide_animation.setStartValue(current_pos)
        self.slide_animation.setEndValue(end_pos)
        self.slide_animation.start()

    def _on_animation_finished(self):
        self.hide()  # Hide widget after animation
        self.itemRemoved.emit()  # Emit signal to trigger removal

    def highlight(self):
        """Highlight the widget with animation"""
        # Set style trực tiếp trước
        self.setStyleSheet("""
            QFrame {
                background-color: #F8FFAA;
                border-radius: 15px;
                padding: 5px;
            }
        """)
        
        # Set style cho tất cả widget con
        for widget in self.findChildren(QWidget):
            current_style = widget.styleSheet()
            widget.setStyleSheet(current_style + "background-color: #F8FFAA;")
        
        # Tạo animation để chuyển về màu trắng sau 5s
        def reset_styles():
            self.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 15px;
                    padding: 5px;
                }
            """)
            for widget in self.findChildren(QWidget):
                widget.setStyleSheet(widget.styleSheet().replace("background-color: #F8FFAA;", "background-color: white;"))
        
        QTimer.singleShot(5000, reset_styles)
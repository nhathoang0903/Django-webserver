from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QFontDatabase
import os

class ProductModal(QFrame):
    add_to_cart = pyqtSignal(dict, int)  
    cancel_clicked = pyqtSignal()  # Add new signal for cancel button


    def __init__(self, parent=None, camera_height=None, camera_width=None):
        super().__init__(parent)
        self.quantity = 1
        self.current_product = None
        self.setFixedWidth(300) 
        self.setFixedHeight(260)  
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 20px;
                border: none;
            }
        """)
        self.init_ui()  # Remove warning_widget

    def load_fonts(self):
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))

    def init_ui(self):
        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Left section - Image
        self.image_label = QLabel()
        # Default size, will be updated in update_product
        self.image_label.setFixedSize(75, 75)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: transparent; 
                border: none; 
            }
        """)
        main_layout.addWidget(self.image_label)

        # Right section
        right_widget = QWidget()
        self.right_layout = QVBoxLayout(right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(5)

        # Product name
        self.name_label = QLabel()
        self.name_label.setFont(QFont("Inria Sans", 12, QFont.Bold))
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumHeight(40)  # Reduced from 50
        self.name_label.setStyleSheet("""
            QLabel {
                qproperty-alignment: AlignCenter;
                padding: 0 10px;  /* Add horizontal padding */
            }
        """)
        self.right_layout.addWidget(self.name_label)

        # Price with more space above
        self.right_layout.addSpacing(10)  # Reduced from 15
        self.price_label = QLabel()
        self.price_label.setFont(QFont("Inria Sans", 8, QFont.Bold))
        self.price_label.setStyleSheet("""
            QLabel {
                color: #D32F2F;
                qproperty-alignment: AlignCenter;
                margin-bottom: 15px;  /* Add bottom margin to price label */
            }
        """)
        self.price_label.setAlignment(Qt.AlignCenter)  # Add center alignment
        self.right_layout.addWidget(self.price_label)
        
        self.right_layout.addSpacing(15)  # Reduced from 25

        # Quantity controls in horizontal layout
        self.quantity_widget = QWidget()
        quantity_layout = QHBoxLayout(self.quantity_widget)
        quantity_layout.setContentsMargins(0, 0, 0, 0)
        quantity_layout.setSpacing(0)  

        self.minus_btn = QPushButton("-")
        self.minus_btn.setFont(QFont("Inria Sans", 13, QFont.Bold))
        self.quantity_label = QLabel("1")
        self.quantity_label.setFont(QFont("Inria Sans", 13, QFont.Bold))
        self.plus_btn = QPushButton("+")
        self.plus_btn.setFont(QFont("Inria Sans", 13, QFont.Bold))

        # Set equal fixed size for all elements
        control_size = 32
        for widget in [self.minus_btn, self.quantity_label, self.plus_btn]:
            widget.setFixedSize(control_size, control_size)

        # Style the minus button with left border radius
        self.minus_btn.setStyleSheet("""
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

        # Style the quantity label
        self.quantity_label.setStyleSheet("""
            QLabel {
                background-color: white;
                color: #000000;
                border: 1px solid #000000;
                font-size: 14px;
                font-weight: bold;
                qproperty-alignment: AlignCenter;
            }
        """)

        # Style the plus button with right border radius
        self.plus_btn.setStyleSheet("""
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

        self.minus_btn.clicked.connect(self.decrease_quantity)
        self.plus_btn.clicked.connect(self.increase_quantity)

        quantity_layout.addWidget(self.minus_btn)
        quantity_layout.addWidget(self.quantity_label)
        quantity_layout.addWidget(self.plus_btn)
        
        # Center the quantity controls
        quantity_container = QHBoxLayout()
        quantity_container.addStretch()
        quantity_container.addWidget(self.quantity_widget)
        quantity_container.addStretch()
        self.right_layout.addLayout(quantity_container)

        # Center the quantity controls with more spacing
        self.right_layout.addSpacing(25)  # Increased spacing before quantity controls

        # Before buttons section, add more vertical space
        self.right_layout.addStretch(1)  # Add stretch to push content up
        
        # Điều chỉnh spacing trước buttons
        self.right_layout.addSpacing(10)  # Giảm spacing trước buttons

        # Buttons section 
        self.buttons_widget = QWidget()
        btn_layout = QHBoxLayout(self.buttons_widget)
        btn_layout.setContentsMargins(0, 0, 0, 10) 
        btn_layout.setSpacing(5)
        
        # Center the buttons
        btn_layout.setAlignment(Qt.AlignCenter)  # Căn giữa các buttons

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(95, 32)
        cancel_btn.setFont(QFont("Inria Sans", 8, QFont.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                 color: #D32F2F;
                border: 1px solid #D30E11;
                border-radius: 13px;
            }
            QPushButton:hover {
                background-color: #D30E11;
                color: white;
            }
        """)
        cancel_btn.clicked.connect(self.handle_cancel)  # Change to new handler

        # Add to cart button
        add_btn = QPushButton("Add to cart")
        add_btn.setFixedSize(95, 32)
        add_btn.setFont(QFont("Inria Sans", 8, QFont.Bold))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #507849;
                border-radius: 13px;
                border: 1px solid #507849;
            }
            QPushButton:hover {
                background-color: #507849;
                color: white;
            }
        """)
        add_btn.clicked.connect(self.add_item_to_cart)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(add_btn)

        # Đảm bảo buttons được căn giữa trong container
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(self.buttons_widget)
        btn_container.addStretch()
        self.right_layout.addLayout(btn_container)

        # Thêm spacing cuối cùng
        self.right_layout.addSpacing(10)

        main_layout.addWidget(right_widget)

    def update_product(self, product):  # Remove is_existing parameter
        self.current_product = product
        self.quantity = 1
        self.quantity_label.setText(str(self.quantity))

        # Format name by replacing underscores with spaces
        formatted_name = product['name'].replace('_', ' ')
        self.name_label.setText(formatted_name)
        
        # Convert price to float and format with dot as thousand separator
        try:
            price_value = float(product['price'])
            formatted_price = "{:,.0f}".format(price_value).replace(',', '.')
        except (ValueError, TypeError):
            formatted_price = product['price']  # Fallback to original if conversion fails
            
        price_text = f'<span style="color: #000000;">Price: </span><span style="color: #D30E11;"><b>{formatted_price} vnd / item</b></span>'
        self.price_label.setText(price_text)

        # Clean up image URL
        image_url = product['image_url']
        if image_url.endswith('.webp'):
            image_url = image_url[:-5]
            
        print(f"Attempting to load image from: {image_url}")
        
        if not image_url:
            print("Warning: No image URL provided")
            return

        # Update image size based on category
        category = product.get('category', '')
        if category == "Đồ ăn vặt":
            image_size = (75, 120)
        elif category == "Thức uống":
            image_size = (75, 140)
        elif category == "Thức ăn":
            image_size = (75, 125)
        else:
            image_size = (75, 75)  # Default size
            
        self.image_label.setFixedSize(*image_size)

        # Create QPixmap from URL
        pixmap = QPixmap()
        from urllib.request import urlopen
        try:
            data = urlopen(image_url).read()
            pixmap.loadFromData(data)
            
            # Scale according to category size
            scaled_pixmap = pixmap.scaled(
                image_size[0], 
                image_size[1],
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Error loading image: {e}")
            # Load default image if URL fails
            default_image_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'assets', 
                'default-product.png'
            )
            pixmap.load(default_image_path)

        if pixmap.isNull():
            print("Error: Failed to load image")
            return

        scaled_pixmap = pixmap.scaled(
            self.image_label.width(), 
            self.image_label.height(),
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        
        self.image_label.setPixmap(scaled_pixmap)

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
            self.hide()  # Hide the modal
            self.cancel_clicked.emit()  # Use existing signal to resume camera

    def handle_cancel(self):
        self.cancel_clicked.emit()  # Emit signal when cancel is clicked
        self.hide()

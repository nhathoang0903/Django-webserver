from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QFontDatabase
from page3_productsinfo import SimpleImageLoader  # Import SimpleImageLoader
import os
from utils.translation import _, get_current_language  # Add translation import

class ProductModal(QFrame):
    add_to_cart = pyqtSignal(dict, int)  
    cancel_clicked = pyqtSignal()  # Add new signal for cancel button


    def __init__(self, parent=None, camera_height=None, camera_width=None):
        super().__init__(parent)
        self.quantity = 1
        self.current_product = None
        self.setFixedWidth(330)  # Tăng từ 320 lên 330
        self.setFixedHeight(280)  # Tăng từ 260 lên 280
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 20px;
                border: none;
            }
        """)
        self.existing_message = None  # Add this line
        self.controls_container = None  # Add this line
        self.init_ui()  # Remove warning_widget

    def load_fonts(self):
        # Register necessary fonts
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/static/Inter_24pt-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/static/Inter_24pt-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/static/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))

    def init_ui(self):
        # Main layout là VBoxLayout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top section container
        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        # Left section - Image
        self.image_label = QLabel()
        self.image_label.setFixedSize(105, 105)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: transparent; 
                border: none; 
            }
        """)
        top_layout.addWidget(self.image_label)

        # Right section
        right_widget = QWidget()
        self.right_layout = QVBoxLayout(right_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(5)

        # Product name
        self.name_label = QLabel()
        self.name_label.setFont(QFont("Inria Sans", 18, QFont.Bold))
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumHeight(55)
        self.name_label.setStyleSheet("""
            QLabel {
                qproperty-alignment: AlignCenter;
                padding: 0 10px;
            }
        """)
        self.right_layout.addWidget(self.name_label)

        self.warning_label = QLabel()
        self.warning_label.setStyleSheet("""
            QLabel {
                color: #D32F2F;
                font-size: 11px;
                font-weight: bold;
                background-color: #FFEBEE;
                border: 1px solid #FFCDD2;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.warning_label.setAlignment(Qt.AlignCenter)
        self.warning_label.hide()
        
        # Add warning label to right_layout after name_label
        self.right_layout.insertWidget(1, self.warning_label)

        # Price with more space above
        self.right_layout.addSpacing(10)
        self.price_label = QLabel()
        self.price_label.setFont(QFont("Inria Sans", 14, QFont.Bold))
        self.price_label.setStyleSheet("""
            QLabel {
                color: #D32F2F;
                qproperty-alignment: AlignCenter;
                margin-bottom: 15px;  
            }
        """)
        self.price_label.setAlignment(Qt.AlignCenter)
        self.right_layout.addWidget(self.price_label)
        
        self.right_layout.addSpacing(15)  

        # Create controls container to hold quantity and buttons
        self.controls_container = QWidget()
        controls_layout = QVBoxLayout(self.controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(5)

        # Move quantity controls and buttons into controls_container
        # Quantity controls
        self.quantity_widget = QWidget()
        quantity_layout = QHBoxLayout(self.quantity_widget)
        quantity_layout.setContentsMargins(0, 0, 0, 0)
        quantity_layout.setSpacing(0)  

        # Increase control size
        control_size = 36 

        self.minus_btn = QPushButton("-")
        self.minus_btn.setFont(QFont("Inria Sans", 18, QFont.Bold))
        self.quantity_label = QLabel("1")
        self.quantity_label.setFont(QFont("Inria Sans", 20, QFont.Bold))
        self.plus_btn = QPushButton("+")
        self.plus_btn.setFont(QFont("Inria Sans", 18, QFont.Bold))

        # Set equal fixed size for all elements
        for widget in [self.minus_btn, self.plus_btn]:
            widget.setFixedSize(control_size, control_size)
        
        # Make quantity label wider to accommodate larger numbers
        self.quantity_label.setFixedSize(control_size + 15, control_size)

        # Style the minus button with left border radius
        self.minus_btn.setStyleSheet("""
            QPushButton {
                background-color: #D8D8D8;
                color: #000000;
                border: none;
                border-radius: 12px;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
            QPushButton:pressed {
                background-color: #A8A8A8;
            }
        """)

        # Style the quantity label
        self.quantity_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #FF0000;
                border: none;
                font-weight: bold;
                qproperty-alignment: AlignCenter;
            }
        """)

        # Style the plus button with right border radius
        self.plus_btn.setStyleSheet("""
            QPushButton {
                background-color: #D8D8D8;
                color: #000000;
                border: none;
                border-radius: 12px;
                font-size: 22px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
            QPushButton:pressed {
                background-color: #A8A8A8;
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
        controls_layout.addLayout(quantity_container)

        # Center the quantity controls with more spacing
        controls_layout.addSpacing(25)

        # Before buttons section, add more vertical space
        self.right_layout.addStretch(1)
        
        # Điều chỉnh spacing trước buttons
        self.right_layout.addSpacing(10)

        # Buttons section 
        self.buttons_widget = QWidget()
        btn_layout = QHBoxLayout(self.buttons_widget)
        btn_layout.setContentsMargins(0, 0, 0, 10) 
        btn_layout.setSpacing(20)  # Tăng khoảng cách giữa các buttons từ 5 thành 20
        
        # Center the buttons
        btn_layout.setAlignment(Qt.AlignCenter)

        # Cancel button - increased size and font
        cancel_btn = QPushButton(_("productModal.cancel"))
        cancel_btn.setFixedSize(90, 40)
        cancel_btn.setFont(QFont("Inria Sans", 12, QFont.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #D32F2F;
                border: 1px solid #D30E11;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #D30E11;
                color: white;
            }
        """)
        cancel_btn.clicked.connect(self.handle_cancel)

        # Add to cart button
        add_btn = QPushButton(_("productModal.addToCart"))
        add_btn.setFixedSize(90, 40)
        add_btn.setFont(QFont("Inria Sans", 12, QFont.Bold))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #507849;
                border-radius: 15px;
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
        controls_layout.addLayout(btn_container)

        # Add controls container to right layout
        self.right_layout.addWidget(self.controls_container)

        # Thêm phần từ trên vào top_layout
        top_layout.addWidget(right_widget)
        main_layout.addWidget(top_container)
        
        # Warning message container - di chuyển xuống dưới cùng
        self.warning_container = QWidget()
        warning_layout = QHBoxLayout(self.warning_container)
        warning_layout.setContentsMargins(5, 5, 5, 5)
        warning_layout.setSpacing(10)
        warning_layout.setAlignment(Qt.AlignCenter)

        # Create warning icon and text
        warning_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'warning.png')
        warning_pixmap = QPixmap(icon_path).scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        warning_icon.setPixmap(warning_pixmap)
        warning_icon.setFixedSize(45, 45)
        warning_icon.setAlignment(Qt.AlignCenter)
        warning_layout.addWidget(warning_icon)

        warning_text = QLabel(_("productModal.alreadyInCart"))
        warning_text.setFont(QFont("Inria Sans", 12, QFont.Bold))
        warning_text.setStyleSheet("color: black; background: transparent;")
        warning_text.setContentsMargins(0, 0, 0, 0)
        warning_text.setMinimumWidth(170)
        warning_text.setFixedWidth(170)
        warning_text.setAlignment(Qt.AlignCenter)
        warning_text.setWordWrap(True)
        warning_layout.addWidget(warning_text)

        self.warning_container.setStyleSheet("""
            QWidget {
                background-color: #F68003;
                border: none;
                border-radius: 15px;
            }
        """)
        self.warning_container.hide()
        
        # Thêm warning container vào cuối layout
        main_layout.addWidget(self.warning_container, 0, Qt.AlignCenter)
        main_layout.addStretch()

    def reset_warning_state(self):
        """Reset warning state has been removed since we're recreating the modal instead"""
        pass  # This method is no longer needed

    def update_product(self, product, existing_quantity=None):
        self.current_product = product
        self.quantity = 1
        self.quantity_label.setText(str(self.quantity))

        # Format name by replacing underscores with spaces
        formatted_name = product['name'].replace('_', ' ')
        self.name_label.setText(formatted_name)
        
        # Format price
        try:
            price_value = float(product['price'])
            formatted_price = "{:,.0f}".format(price_value).replace(',', '.')
        except (ValueError, TypeError):
            formatted_price = product['price']
            
        price_text = f'<span style="color: #D30E11;"><b>{formatted_price} vnđ / item</b></span>'
        self.price_label.setText(price_text)

        # Get image size based on category
        category = product.get('category', '')
        if category == "Snack":
            image_size = (95, 140)  
        elif category == "Food":
            image_size = (95, 160)  
        elif category == "Beverage":
            image_size = (95, 145) 
        else:
            image_size = (95, 95) 
            
        self.image_label.setFixedSize(*image_size)

        # Try to get cached image first
        image_url = product['image_url']
        cache_key = f"{image_url}_{image_size[0]}x{image_size[1]}"
        
        if cache_key in SimpleImageLoader._cache:
            # Use cached image if available
            self.image_label.setPixmap(SimpleImageLoader._cache[cache_key])
        else:
            # If not in cache, load using SimpleImageLoader
            pixmap = SimpleImageLoader.load_image(image_url, image_size)
            if pixmap:
                self.image_label.setPixmap(pixmap)
            else:
                # Load default image if failed
                default_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), 
                    'assets', 
                    'default-product.png'
                )
                default_pixmap = QPixmap(default_path)
                scaled = default_pixmap.scaled(
                    image_size[0], image_size[1],
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled)

        # Toggle visibility
        if existing_quantity is not None:
            # Trường hợp có warning (sản phẩm đã có trong giỏ hàng)
            self.controls_container.hide()
            self.warning_label.hide()
            
            # Hiển thị warning container
            self.warning_container.show()
            self.warning_container.raise_()
        else:
            # Trường hợp bình thường
            self.controls_container.show()
            self.warning_label.hide()
            
            # Ẩn warning container
            self.warning_container.hide()

    def increase_quantity(self):
        self.quantity += 1
        self.quantity_label.setText(str(self.quantity))

    def decrease_quantity(self):
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.setText(str(self.quantity))

    def add_item_to_cart(self):
        """Add item to cart with safety checks"""
        if self.current_product and not self.isHidden():
            self.add_to_cart.emit(self.current_product, self.quantity)

    def handle_cancel(self):
        """Handle cancel button click"""
        self.cancel_clicked.emit()  # Emit signal for parent to handle
        self.hide()

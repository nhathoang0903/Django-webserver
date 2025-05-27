from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QFont, QFontDatabase
from page3_productsinfo import SimpleImageLoader
import os
from utils.translation import _, get_current_language 

class ProductModal(QFrame):
    add_to_cart = pyqtSignal(dict, int)  
    cancel_clicked = pyqtSignal()  


    def __init__(self, parent=None, camera_height=None, camera_width=None):
        super().__init__(parent)
        self.quantity = 1
        self.current_product = None
        self.setFixedWidth(700)
        self.setFixedHeight(550) 
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 30px;
                border: none; 
            }
        """)
        
        # Thêm hiệu ứng đổ bóng thay vì dùng box-shadow CSS
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(Qt.gray)
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)
        
        # Add cooldown mechanism to prevent rapid clicking
        self.button_cooldown = False
        self.cooldown_timer = QTimer(self)
        self.cooldown_timer.timeout.connect(self.reset_cooldown)
        self.cooldown_duration = 1000  # milliseconds between clicks
        
        self.existing_message = None
        self.controls_container = None
        self.init_ui()

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
        main_layout.setContentsMargins(30, 30, 30, 30)  
        main_layout.setSpacing(15) 

        # ========= TOP SECTION =========
        # Top section container for image and product info
        top_container = QWidget()
        top_container.setStyleSheet("background-color: transparent; border: none;")
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(30)

        # Left section - Image
        self.image_label = QLabel()
        self.image_label.setFixedSize(280, 280)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: transparent; 
                border: none; 
            }
        """)
        top_layout.addWidget(self.image_label, 0, Qt.AlignCenter)

        # Right section - Product Info
        right_widget = QWidget()
        right_widget.setStyleSheet("background-color: transparent; border: none;")
        self.right_layout = QVBoxLayout(right_widget)
        self.right_layout.setContentsMargins(30, 0, 15, 0)
        self.right_layout.setSpacing(15)

        # Product name
        self.name_label = QLabel()
        self.name_label.setFont(QFont("Inria Sans", 30, QFont.Bold))
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumHeight(100)
        self.name_label.setStyleSheet("""
            QLabel {
                qproperty-alignment: 'AlignLeft | AlignVCenter';
                padding-left: 10px;
            }
        """)
        self.right_layout.addWidget(self.name_label)

        # Warning label
        self.warning_label = QLabel()
        self.warning_label.setStyleSheet("""
            QLabel {
                color: #D32F2F;
                font-size: 16px;
                font-weight: bold;
                background-color: #FFEBEE;
                border: 1px solid #FFCDD2;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        self.warning_label.setAlignment(Qt.AlignCenter)
        self.warning_label.hide()
        self.right_layout.insertWidget(1, self.warning_label)

        # Price with more space above
        self.right_layout.addSpacing(25)
        self.price_label = QLabel()
        self.price_label.setFont(QFont("Inria Sans", 26, QFont.Bold))
        self.price_label.setStyleSheet("""
            QLabel {
                color: #D32F2F;
                qproperty-alignment: 'AlignLeft | AlignVCenter';
                margin-bottom: 25px;
                padding-left: 5x;
            }
        """)
        self.price_label.setAlignment(Qt.AlignLeft)
        self.right_layout.addWidget(self.price_label)
        
        self.right_layout.addSpacing(15)

        # Quantity controls
        self.quantity_widget = QWidget()
        self.quantity_widget.setStyleSheet("background-color: transparent; border: none;")
        quantity_layout = QHBoxLayout(self.quantity_widget)
        quantity_layout.setContentsMargins(0, 0, 0, 0)
        quantity_layout.setSpacing(0)

        # Control size
        control_size = 74

        self.minus_btn = QPushButton("-")
        self.minus_btn.setFont(QFont("Inria Sans", 28, QFont.Bold))
        self.quantity_label = QLabel("1")
        self.quantity_label.setFont(QFont("Inria Sans", 30, QFont.Bold))
        self.plus_btn = QPushButton("+")
        self.plus_btn.setFont(QFont("Inria Sans", 28, QFont.Bold))

        # Set equal fixed size for all elements
        for widget in [self.minus_btn, self.plus_btn]:
            widget.setFixedSize(control_size, control_size)
        
        # Make quantity label wider to accommodate larger numbers
        self.quantity_label.setFixedSize(control_size + 30, control_size)

        # Style the minus button with left border radius
        self.minus_btn.setStyleSheet("""
            QPushButton {
                background-color: #D8D8D8;
                color: #000000;
                border: none;
                border-radius: 20px;
                font-size: 46px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
            QPushButton:pressed {
                background-color: #A8A8A8;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #909090;
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
                border-radius: 20px;
                font-size: 46px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
            QPushButton:pressed {
                background-color: #A8A8A8;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #909090;
            }
        """)

        self.minus_btn.clicked.connect(self.decrease_quantity)
        self.plus_btn.clicked.connect(self.increase_quantity)

        quantity_layout.addWidget(self.minus_btn)
        quantity_layout.addWidget(self.quantity_label)
        quantity_layout.addWidget(self.plus_btn)
        
        # Add quantity widget with some left margin
        quantity_container = QHBoxLayout()
        quantity_container.setContentsMargins(20, 0, 0, 0)
        quantity_container.addWidget(self.quantity_widget)
        quantity_container.addStretch()
        self.right_layout.addLayout(quantity_container)
        
        # Add stretch to push content up
        self.right_layout.addStretch(1)

        # Add right widget to top layout
        top_layout.addWidget(right_widget)
        
        # Add top container to main layout
        main_layout.addWidget(top_container)
        
        # Add spacing between top and bottom sections
        main_layout.addSpacing(20)
        
        # ========= BOTTOM SECTION =========
        # Buttons section with centered buttons
        buttons_container = QWidget()
        buttons_container.setStyleSheet("background-color: transparent; border: none;")
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 10, 0, 10)
        buttons_layout.setSpacing(30)  # Increased spacing between buttons
        buttons_layout.setAlignment(Qt.AlignCenter)  # Center the buttons

        # Cancel button
        self.cancel_btn = QPushButton(_("productModal.cancel"))
        self.cancel_btn.setFixedSize(200, 80)
        self.cancel_btn.setFont(QFont("Inria Sans", 19, QFont.Bold))
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #D32F2F;
                border: 3px solid #D30E11;
                border-radius: 38px;
            }
            QPushButton:hover {
                background-color: #D30E11;
                color: white;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
                border: 3px solid #999999;
            }
        """)
        self.cancel_btn.clicked.connect(self.handle_cancel)

        # Add to cart button
        self.add_btn = QPushButton(_("productModal.addToCart"))
        self.add_btn.setFixedSize(200, 80)
        self.add_btn.setFont(QFont("Inria Sans", 19, QFont.Bold))
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #507849;
                border-radius: 38px;
                border: 3px solid #507849;
            }
            QPushButton:hover {
                background-color: #507849;
                color: white;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
                border: 3px solid #999999;
            }
        """)
        self.add_btn.clicked.connect(self.add_item_to_cart)

        # Add buttons to layout
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.add_btn)
        
        # Add buttons container to main layout
        main_layout.addWidget(buttons_container)
        
        # Add stretch to push buttons up
        main_layout.addStretch(1)
        
        # ========= WARNING CONTAINER (BOTTOM) =========
        # Warning message container
        self.warning_container = QWidget()
        warning_layout = QHBoxLayout(self.warning_container)
        warning_layout.setContentsMargins(15, 15, 15, 15)
        warning_layout.setSpacing(20)
        warning_layout.setAlignment(Qt.AlignCenter)

        # Create warning icon and text
        warning_icon = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'warning.png')
        warning_pixmap = QPixmap(icon_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        warning_icon.setPixmap(warning_pixmap)
        warning_icon.setFixedSize(80, 80)
        warning_icon.setAlignment(Qt.AlignCenter)
        warning_layout.addWidget(warning_icon)

        warning_text = QLabel(_("productModal.alreadyInCart"))
        warning_text.setFont(QFont("Inria Sans", 22, QFont.Bold))
        warning_text.setStyleSheet("color: black; background: transparent;")
        warning_text.setContentsMargins(0, 0, 0, 0)
        warning_text.setMinimumWidth(320)
        warning_text.setFixedWidth(320)
        warning_text.setAlignment(Qt.AlignCenter)
        warning_text.setWordWrap(True)
        warning_layout.addWidget(warning_text)

        self.warning_container.setStyleSheet("""
            QWidget {
                background-color: #F68003;
                border: none;
                border-radius: 25px;
            }
        """)
        self.warning_container.hide()
        
        # Add warning container to main layout
        main_layout.addWidget(self.warning_container, 0, Qt.AlignCenter)

    def reset_warning_state(self):
        """Reset warning state has been removed since we're recreating the modal instead"""
        pass  # This method is no longer needed
        
    def reset_cooldown(self):
        """Reset the button cooldown state"""
        self.button_cooldown = False
        print("[ProductModal] Button cooldown ended")

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

        # Get image size based on category - increased sizes
        category = product.get('category', '')
        if category == "Snack":
            image_size = (280, 330)
        elif category == "Food":
            image_size = (280, 360)
        elif category == "Beverage":
            image_size = (280, 350)
        else:
            image_size = (280, 280)
            
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
            self.quantity_widget.hide()
            self.warning_label.hide()
            
            # Hiển thị warning container và ẩn các nút
            self.warning_container.show()
            self.warning_container.raise_()
            self.cancel_btn.hide()
            self.add_btn.hide()
        else:
            # Trường hợp bình thường
            self.quantity_widget.show()
            self.warning_label.hide()
            
            # Ẩn warning container và hiện các nút
            self.warning_container.hide()
            self.cancel_btn.show()
            self.add_btn.show()

    def increase_quantity(self):
        # Check if we're in cooldown period
        if self.button_cooldown:
            return
            
        # Apply cooldown
        self.button_cooldown = True
        
        # Increment quantity
        self.quantity += 1
        self.quantity_label.setText(str(self.quantity))
        
        # Start cooldown timer
        self.cooldown_timer.start(self.cooldown_duration)

    def decrease_quantity(self):
        # Check if we're in cooldown period
        if self.button_cooldown:
            return
            
        # Apply cooldown
        self.button_cooldown = True
        
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.setText(str(self.quantity))
            
            # Start cooldown timer
            self.cooldown_timer.start(self.cooldown_duration)
        else:
            # Reset cooldown since we didn't change anything
            self.button_cooldown = False

    def add_item_to_cart(self):
        """Add item to cart with safety checks"""
        if self.current_product and not self.isHidden():
            self.add_to_cart.emit(self.current_product, self.quantity)

    def handle_cancel(self):
        """Handle cancel button click"""
        self.cancel_clicked.emit()  # Emit signal for parent to handle
        self.hide()

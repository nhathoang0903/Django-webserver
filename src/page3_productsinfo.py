from base_page import BasePage  
from components.PageTransitionOverlay import PageTransitionOverlay
from components.ProductCardDialog import ProductCardDialog 
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                           QGridLayout, QApplication, QFrame, QHBoxLayout, QScroller, QComboBox, QPushButton, QMenu, QDialog, QGraphicsBlurEffect, QLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QEvent, QSize, QPropertyAnimation, QEasingCurve, QTimer, QFileSystemWatcher
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase, QMovie, QIcon
import os
import json
import urllib.request
from urllib.error import URLError
import threading
from page_timing import PageTiming
from cart_state import CartState
import requests
from config import CART_END_SESSION_API, DEVICE_ID
import importlib
import sys

class SimpleImageLoader:
    _cache = {}  # Add image cache

    @staticmethod
    def load_image(url, size=(75, 75)):
        # Check cache first
        cache_key = f"{url}_{size[0]}x{size[1]}"
        if cache_key in SimpleImageLoader._cache:
            return SimpleImageLoader._cache[cache_key]

        try:
            # Convert URL to use images.weserv.nl proxy
            if not url.startswith('https://images.weserv.nl'):
                proxy_url = f"https://images.weserv.nl/?url={url}"
            else:
                proxy_url = url

            # Add timeout to prevent hanging
            request = urllib.request.Request(
                proxy_url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            data = urllib.request.urlopen(request, timeout=5).read()  # Increased timeout
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            
            # Scale image before caching
            scaled = pixmap.scaled(size[0], size[1], 
                                 Qt.KeepAspectRatio, 
                                 Qt.SmoothTransformation)
            
            # Cache the scaled image
            SimpleImageLoader._cache[cache_key] = scaled
            return scaled

        except Exception as e:
            print(f"Error loading image {url}: {e}")
            # Load and cache default image
            default_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'assets', 
                'default-product.png'
            )
            default_pixmap = QPixmap(default_path)
            scaled = default_pixmap.scaled(size[0], size[1],
                                         Qt.KeepAspectRatio,
                                         Qt.SmoothTransformation)
            SimpleImageLoader._cache[cache_key] = scaled
            return scaled

class ProductCard(QFrame):
    clicked = pyqtSignal(dict)  # Add signal to emit product data
    
    def __init__(self, product):
        super().__init__()
        self.product = product
        self.cached_image = None  # Store cached image
        self.cart_state = CartState()  # Add CartState instance
        self.setup_ui()
        self.load_image_async()
        self.setCursor(Qt.PointingHandCursor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.product)  # Emit signal with product data
            
    def show_product_modal(self, product):
        # Create overlay for blur effect
        self._overlay = QWidget(self)
        self._overlay.setGeometry(self.rect())
        self._overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
        self._overlay.show()
        
        # Create modal container
        self._modal = QFrame(self)
        self._modal.setFixedSize(350, 400)
        self._modal.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                border: none;
            }
        """)
        
        # Position modal in center of parent
        parent_rect = self.geometry()
        self._modal.move(
            (parent_rect.width() - self._modal.width()) // 2,
            (parent_rect.height() - self._modal.height()) // 2
        )
        
        # Create layout
        layout = QVBoxLayout(self._modal)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(5)  # Reduced spacing between components
        
        # Close button (X) at the top right
        close_btn = QPushButton("×")
        close_btn.setFixedSize(40, 40)  # Increased size
        close_btn.setFont(QFont("Arial", 16, QFont.Bold))  # Increased font size
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666;
                border: none;
                border-radius: 20px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                color: #333;
            }
        """)
        
        # Create a container for the close button
        close_container = QWidget()
        close_container.setStyleSheet("background-color: transparent;")
        close_layout = QHBoxLayout(close_container)
        close_layout.setContentsMargins(0, 0, 0, 0)
        close_layout.addStretch()
        close_layout.addWidget(close_btn)
        
        # Add close button container to main layout
        layout.addWidget(close_container)
        
        # Image with larger size to fit the modal
        image_label = QLabel()
        if product.get('image_url'):
            pixmap = SimpleImageLoader.load_image(product['image_url'], (180, 180))
            if pixmap:
                image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet("border: none;")
        layout.addWidget(image_label)
        
        # Name
        name = product['name'].replace('_', ' ')
        name_label = QLabel(name)
        name_label.setFont(QFont("Josefin Sans", 12, QFont.Bold))
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("border: none;")
        layout.addWidget(name_label)
        
        # Price
        price = "{:,.0f}".format(float(product['price'])).replace(',', '.')
        price_label = QLabel(f"{price} vnd")
        price_label.setFont(QFont("Josefin Sans", 10))
        price_label.setStyleSheet("color: #E72225; border: none;")
        price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(price_label)
        
        # Category
        category_label = QLabel(f"Category: {product['category']}")
        category_label.setFont(QFont("Josefin Sans", 12))
        category_label.setStyleSheet("color: black; border: none;")
        category_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(category_label)
        
        # Description
        desc_label = QLabel(product['description'])
        desc_label.setFont(QFont("Josefin Sans", 11))
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666; border: none;")
        layout.addWidget(desc_label)
        
        # Connect close button
        close_btn.clicked.connect(self.close_modal)
        
        # Show modal and overlay
        self._modal.show()
        self._modal.raise_()
        
        # Handle click outside modal
        def handle_click(event):
            if not self._modal.geometry().contains(event.pos()):
                self.close_modal()
        
        self._overlay.mousePressEvent = handle_click

    def close_modal(self):
        if self._modal:
            self._modal.close()
            self._modal = None
        if self._overlay:
            self._overlay.close()
            self._overlay = None

    def load_image_async(self):
        def load():
            pixmap = SimpleImageLoader.load_image(self.product['image_url'])
            if pixmap:
                self.cached_image = pixmap  # Cache the image
                self.image_label.setPixmap(pixmap)
            else:
                self.image_label.setText("N/A")

        threading.Thread(target=load, daemon=True).start()

    def setup_ui(self):
        self.setFixedSize(140, 180)  # Reduced card width from 160 to 140
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 12px;
                padding: 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(1)
        layout.setSizeConstraint(QLayout.SetFixedSize)

        # Image placeholder
        self.image_label = QLabel()
        self.image_label.setFixedSize(65, 65)  # Reduced image size from 75 to 65
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText("Loading...")
        self.image_label.setStyleSheet("color: #3D6F4A;")
        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        # Name container with fixed size
        name_container = QWidget()
        name_container.setFixedSize(130, 40)  # Reduced width from 150 to 130
        name_layout = QVBoxLayout(name_container)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(0)
        
        # Name
        name = self.product['name'].replace('_', ' ')
        name_label = QLabel(name)
        name_label.setFont(QFont("Josefin Sans", 10))
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        name_label.setFixedWidth(120)  # Reduced width from 140 to 120
        name_label.setStyleSheet("""
            QLabel {
                color: black;
                padding: 0px 5px;
            }
        """)
        name_layout.addWidget(name_label)
        layout.addWidget(name_container)

        # Price
        price = "{:,.0f}".format(float(self.product['price'])).replace(',', '.')
        price_label = QLabel(f"{price} vnd")
        price_label.setFont(QFont("Josefin Sans", 8))
        price_label.setAlignment(Qt.AlignCenter)
        price_label.setStyleSheet("color: #E72225;")
        layout.addWidget(price_label)

        # Add to Cart button
        self.add_to_cart_btn = QPushButton("Add to Cart")
        self.add_to_cart_btn.setFont(QFont("Josefin Sans", 8))
        self.add_to_cart_btn.setCursor(Qt.PointingHandCursor)
        self.add_to_cart_btn.setFixedHeight(25)
        self.add_to_cart_btn.setStyleSheet("""
            QPushButton {
                background-color: #507849;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 3px 8px;
                margin: 1px 10px;
            }
            QPushButton:hover {
                background-color: #3D6F4A;
            }
            QPushButton:pressed {
                background-color: #2C513A;
            }
        """)
        self.add_to_cart_btn.clicked.connect(self.add_to_cart)
        layout.addWidget(self.add_to_cart_btn)
        
    def add_to_cart(self):
        try:
            # Add 1 item by default from product page
            is_existing = self.cart_state.add_item(self.product, 1)

            # Update the cart count to reflect the total number of items in detected_products
            from count_item import update_cart_count
            update_cart_count(self)

            # Visual feedback
            self.add_to_cart_btn.setText("Added!" if not is_existing else "Added More!")
            QTimer.singleShot(1000, lambda: self.add_to_cart_btn.setText("Add to Cart"))
        except Exception as e:
            print(f"Error adding to cart: {e}")

class LoadProductsThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                   'json', 'products.json')
            with open(json_path, 'r', encoding='utf-8') as file:
                products = json.load(file)

            # Pre-load images in batches to avoid overwhelming network
            batch_size = 4
            for i in range(0, min(16, len(products)), batch_size):
                batch = products[i:i+batch_size]
                threads = []
                for product in batch:
                    thread = threading.Thread(
                        target=SimpleImageLoader.load_image,
                        args=(product['image_url'],),
                        daemon=True
                    )
                    threads.append(thread)
                    thread.start()
                
                # Wait for batch to complete
                for thread in threads:
                    thread.join(timeout=3)  # Timeout after 3 seconds

            self.finished.emit(products)
            
        except Exception as e:
            self.error.emit(str(e))

class CategoryDropdown(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 40)
        self.setText("All Categories")
        self.setFont(QFont("Josefin Sans", 11))
        self.setCursor(Qt.PointingHandCursor)
        
        # Style for main button
        self.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #3D6F4A;
                border-radius: 8px;
                padding: 5px 15px;
                color: #3D6F4A;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
        """)
        
        # Create custom dropdown menu
        self.menu = QMenu(self)
        self.menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 2px solid #3D6F4A;
                border-radius: 8px;
                padding: 5px;
                min-width: 140px;
            }
            QMenu::item {
                padding: 8px 15px;
                border-radius: 4px;
                color: #3D6F4A;
                font-family: 'Josefin Sans';
                font-size: 11pt;
            }
            QMenu::item:selected {
                background-color: #EEF5F0;
            }
            QMenu::item:pressed {
                background-color: #3D6F4A;
                color: white;
            }
        """)
        
        # Add categories
        categories = ["All Categories", "Beverage", "Food", "Snack"]
        for category in categories:
            action = self.menu.addAction(category)
            action.triggered.connect(lambda checked, c=category: self.on_category_selected(c))
        
        # Show dropdown on click
        self.clicked.connect(self.show_menu)
        
    def show_menu(self):
        # Calculate position for dropdown to appear below button
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self.menu.popup(pos)
        
    def on_category_selected(self, category):
        self.setText(category)
        self.parent().filter_products(category)

class ProductPage(BasePage):  # Changed from QWidget to BasePage
    _instance = None
    _products_cache = None
    _cards_cache = []
    _modal = None
    _overlay = None
    _watcher = None  # Add file watcher

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProductPage, cls).__new__(cls)
            cls._instance._needs_init = True
        return cls._instance

    def __init__(self):
        if hasattr(self, '_needs_init') and self._needs_init:
            super().__init__()  # Call BasePage init
            self.setObjectName("ProductPage")  # Add this line
            self.installEventFilter(self)  # Register event filter
            self._needs_init = False  
            self._fonts_loaded = False
            self.init_ui()
            
            # Initialize transition overlay
            self.transition_overlay = PageTransitionOverlay(self)
            
            if not ProductPage._products_cache:
                self.setup_loading_indicator()
                self.start_loading_products()
            else:
                self.display_cached_products()
                
            # Set application icon
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
            self.setWindowIcon(QIcon(icon_path))

    def reload_current_page(self):
        """Reload the current page"""
        try:
            # Store current state
            current_products = ProductPage._products_cache
            current_cards = ProductPage._cards_cache
            
            # Clear cache
            ProductPage._products_cache = None
            ProductPage._cards_cache = []
            
            # Reinitialize the page
            self._needs_init = True
            self.__init__()
            
            # Restore state
            ProductPage._products_cache = current_products
            ProductPage._cards_cache = current_cards
            
            # Redisplay products
            self.display_cached_products()
            
        except Exception as e:
            print(f"Error reloading current page: {str(e)}")

    def display_cached_products(self):
        """Display products from cache without reloading"""
        if ProductPage._products_cache and ProductPage._cards_cache:
            # Restore cached cards to grid
            for i, card in enumerate(ProductPage._cards_cache):
                row = (i // 4) * 2
                col = i % 4
                self.grid_layout.addWidget(card, row, col)
                
    def on_products_loaded(self, products):
        """Modified to show all products without limit"""
        self.gif_movie.stop()
        self.loading_widget.hide()
        
        ProductPage._products_cache = products
        font_family = self.load_fonts()
        
        # Create and cache all product cards with fixed positions
        ProductPage._cards_cache = []
        for i, product in enumerate(products):
            row = (i // 4) * 2
            col = i % 4
            card = ProductCard(product)
            card.font_family = font_family
            # Connect card's clicked signal to show_product_modal
            card.clicked.connect(self.show_product_modal)
            # Store original position
            card.grid_pos = (row, col)
            self.grid_layout.addWidget(card, row, col)
            ProductPage._cards_cache.append(card)
            if (i + 1) % 4 == 0:
                QApplication.processEvents()

    def closeEvent(self, event):
        """Keep cache when closing"""
        # Don't clear cache here
        super().closeEvent(event)

    @classmethod
    def clear_cache(cls):
        """Method to manually clear cache if needed"""
        cls._products_cache = None
        cls._cards_cache = []
        if cls._instance:
            cls._instance = None

    def load_fonts(self):
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'font-family')
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Tillana/Tillana-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inria_Sans/InriaSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Italic.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Inter/Inter-Bold.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Poppins/Poppins-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Josefin_Sans/JosefinSans-Regular.ttf'))
        QFontDatabase.addApplicationFont(os.path.join(font_dir, 'Baloo/Baloo-Regular.ttf'))

    def init_ui(self):
        self.setWindowTitle('Product Information - Smart Shopping Cart')
        # Remove setGeometry and setFixedSize since handled by BasePage
        self.setStyleSheet(f"background-color: #EEF5F0;")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 0, 30, 8)  # Reduced top margin to 0
        main_layout.setSpacing(0)  # Remove all spacing between elements

        # Top section with logo and header
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        
        # Logo
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            logo_label.setPixmap(logo_pixmap.scaled(154, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top_layout.addWidget(logo_label)

        # Header
        header_label = QLabel("Product Information")
        header_label.setFont(QFont("Inria Sans", 28))
        header_label.setStyleSheet("color: #3D6F4A;")
        header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top_layout.addWidget(header_label)
        
        # Category dropdown
        self.category_dropdown = CategoryDropdown(self)
        top_layout.addWidget(self.category_dropdown)
        
        # Add home button
        home_button = QPushButton()
        home_button.setFixedSize(40, 40)  
        home_button.setCursor(Qt.PointingHandCursor)
        home_button.setStyleSheet("""
            QPushButton {
                background-color: #507849;
                border: none;
                border-radius: 20px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #3e5c38;
            }
        """)
        
        # Add home icon
        home_icon = QLabel()
        home_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'home.png')
        home_pixmap = QPixmap(home_icon_path)
        if not home_pixmap.isNull():
            home_icon.setPixmap(home_pixmap.scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        home_icon.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                padding: 0px;
            }
        """)
        
        # Create container for icon
        icon_container = QWidget()
        icon_container.setFixedSize(30, 30) 
        icon_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
                border-radius: 15px; 
            }
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(home_icon, alignment=Qt.AlignCenter)
        home_button.setLayout(icon_layout)
        
        # Connect home button to return to page1
        home_button.clicked.connect(self.return_to_welcome)
        top_layout.addWidget(home_button)
        
        # Add stretch to push everything to the left
        top_layout.addStretch()

        main_layout.addLayout(top_layout)
        
        # Add minimal spacing between top layout and scroll area
        main_layout.addSpacing(-12)  

        # Scroll Area for products
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(390)  # Increased from 380 to 390
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
                margin-right: 0px;
                margin-top: -12px;
                margin-bottom: 5px;  /* Add bottom margin */
            }
            QScrollBar:vertical {
                border: none;
                background: white;
                border-radius: 10px;
                width: 25px;
                margin: 8px 0px 8px 0px;  /* Increased from 5px to 8px */
                height: 364px;  /* Adjusted to accommodate increased margins */
                subcontrol-origin: margin;
                subcontrol-position: top;
            }
            QScrollBar::handle:vertical {
                background: #D9D9D9;
                border-radius: 10px;
                min-height: 30px;
                margin: 2px;  /* Added margin all around handle */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
                border: none;
            }
            QScrollBar:horizontal {
                height: 0px;
                background: transparent;
                border: none;
                display: none;
            }
        """)

        # Custom gesture handling
        class GestureFilter(QObject):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.start_pos = None
                self.min_distance = 10  # Minimum distance for swipe

            def eventFilter(self, obj, event):
                if event.type() == QEvent.MouseButtonPress:
                    self.start_pos = event.pos()
                    return True
                elif event.type() == QEvent.MouseMove and self.start_pos:
                    current_pos = event.pos()
                    dx = current_pos.x() - self.start_pos.x()
                    dy = current_pos.y() - self.start_pos.y()
                    
                    # Only process vertical movement
                    if abs(dy) > self.min_distance:
                        # Calculate scroll amount based on vertical movement
                        scroll_amount = dy * 0.5  # Adjust sensitivity
                        scroll_area.verticalScrollBar().setValue(
                            scroll_area.verticalScrollBar().value() - int(scroll_amount)
                        )
                        self.start_pos = current_pos
                    return True
                elif event.type() == QEvent.MouseButtonRelease:
                    self.start_pos = None
                    return True
                return False

        # Install gesture filter
        gesture_filter = GestureFilter(scroll_area)
        scroll_area.viewport().installEventFilter(gesture_filter)

        # Container widget for the grid
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.container.setFixedWidth(600)
        self.container.setMinimumHeight(380)  # Increased from 360 to 380
        
        # Grid layout for products
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(25)  
        self.grid_layout.setContentsMargins(10, 10, 60, 20)  # Increased bottom margin from 10 to 20
        self.grid_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)

        scroll_area.setWidget(self.container)
        main_layout.addWidget(scroll_area)

        # Create a horizontal layout for the bottom section
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the first part (left side) with cart labels
        left_part = QHBoxLayout()
        left_part.setSpacing(2)
        
        # Add "Your Cart" text with black color
        your_cart_text = QLabel("Your Cart")
        your_cart_text.setFont(QFont("Josefin Sans", 14, QFont.Bold))
        your_cart_text.setStyleSheet("color: black;")
        left_part.addWidget(your_cart_text)
        
        # Add item count with red color
        cart_count_text = QLabel("(0)")
        cart_count_text.setFont(QFont("Josefin Sans", 14, QFont.Bold))
        cart_count_text.setStyleSheet("color: #E72225;")
        left_part.addWidget(cart_count_text)
        
        # Create container for the entire bottom section with fixed height 
        bottom_container = QWidget()
        bottom_container.setFixedHeight(45)  # Reduced from 50 to 45
        bottom_container_layout = QHBoxLayout(bottom_container)
        bottom_container_layout.setContentsMargins(20, 0, 20, 0)
        
        # Create 3 equal width sections
        left_widget = QWidget()
        left_widget.setLayout(left_part)
        
        middle_widget = QWidget()
        middle_layout = QHBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        
        right_widget = QWidget()  # Empty right widget for spacing
        
        # Add all sections with equal width
        bottom_container_layout.addWidget(left_widget, 1)  # Stretch factor 1
        bottom_container_layout.addWidget(middle_widget, 1)  # Stretch factor 1
        bottom_container_layout.addWidget(right_widget, 1)  # Stretch factor 1
        
        # Create SCAN button
        button_container = QWidget()
        button_container.setCursor(Qt.PointingHandCursor)
        button_container.setFixedSize(160, 40)
        button_container.setStyleSheet("""
            QWidget {
                background-color: #507849;
                border-radius: 20px;
            }
        """)
        
        # Create button content layout
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 0, 10, 0)
        button_layout.setSpacing(10)
        
        # Add scan icon with both normal and hover states
        scan_icon = QLabel()
        scan_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'scanbutton.png')
        scan_hover_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'scanbutton_hover.png')
        self.normal_pixmap = QPixmap(scan_icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.hover_pixmap = QPixmap(scan_hover_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scan_icon.setPixmap(self.normal_pixmap)
        
        # Add SCAN text
        scan_text = QLabel("SCAN")
        scan_text.setFont(QFont("Inter", 12, QFont.Bold))
        scan_text.setStyleSheet("color: white;")
        
        # Add widgets to button layout
        button_layout.addWidget(scan_icon)
        button_layout.addWidget(scan_text)
        button_layout.addStretch()

        # Add SCAN button to center widget
        middle_layout.addWidget(button_container, 0, Qt.AlignCenter)

        # Create event filters for hover effect
        class HoverEventFilter(QObject):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.normal_pixmap = self.parent().normal_pixmap
                self.hover_pixmap = self.parent().hover_pixmap

            def eventFilter(self, obj, event):
                if event.type() == QEvent.Enter:
                    scan_text.setStyleSheet("color: #FFFF00;")
                    scan_icon.setPixmap(self.hover_pixmap)
                    return True
                elif event.type() == QEvent.Leave:
                    scan_text.setStyleSheet("color: white;")
                    scan_icon.setPixmap(self.normal_pixmap)
                    return True
                elif event.type() == QEvent.MouseButtonPress:
                    self.parent().show_shopping_page()
                    return True
                return False

        # Install event filter
        button_container.installEventFilter(HoverEventFilter(self))

        # Add bottom container to main layout
        main_layout.addWidget(bottom_container)

        # Save references to the cart labels for updates
        self.cart_text_label = your_cart_text
        self.cart_count_label = cart_count_text

    def setup_loading_indicator(self):
        self.loading_widget = QWidget(self)
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setSpacing(10)  # Thêm khoảng cách giữa các widget
        
        # Create loading text
        loading_text = QLabel("Loading products...")
        loading_text.setFont(QFont("Poppins", 11))
        loading_text.setStyleSheet("color: #3D6F4A;")
        loading_text.setAlignment(Qt.AlignCenter)
        
        # Create loading GIF
        loading_gif = QLabel()
        loading_gif_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'loading_gif.gif')
        self.gif_movie = QMovie(loading_gif_path)
        self.gif_movie.setScaledSize(QSize(100, 100))  
        loading_gif.setMovie(self.gif_movie)
        self.gif_movie.start()
        
        loading_layout.addWidget(loading_text, alignment=Qt.AlignCenter)
        loading_layout.addWidget(loading_gif, alignment=Qt.AlignCenter)
        
        # Position the loading widget in the center of the page
        self.loading_widget.setGeometry(300, 150, 200, 200)
        self.loading_widget.show()

    def start_loading_products(self):
        self.loading_thread = LoadProductsThread()
        self.loading_thread.finished.connect(self.on_products_loaded)
        self.loading_thread.error.connect(self.on_loading_error)
        self.loading_thread.start()

    def on_loading_error(self, error_message):
        self.loading_widget.hide()
        error_label = QLabel(f"Error loading products: {error_message}")
        error_label.setStyleSheet("color: red;")
        self.grid_layout.addWidget(error_label, 0, 0)

    def show_shopping_page(self):
        """Enhanced transition to shopping page"""
        def switch_page():
            start_time = PageTiming.start_timing()
            from page4_shopping import ShoppingPage
            self.shopping_page = ShoppingPage()
            
            def show_new_page():
                self.shopping_page.show()
                self.transition_overlay.fadeOut(lambda: self.hide())
                PageTiming.end_timing(start_time, "ProductPage", "ShoppingPage")
                
            self.transition_overlay.fadeIn(show_new_page)
            
        switch_page()

    def filter_products(self, category):
        # Hide all cards and remove from layout
        for card in ProductPage._cards_cache:
            card.hide()
            self.grid_layout.removeWidget(card)

        if (category == "All Categories"):
            # Restore original positions for all cards
            for card in ProductPage._cards_cache:
                row, col = card.grid_pos
                self.grid_layout.addWidget(card, row, col)
                card.show()
        else:
            # Filter and rearrange matching cards
            filtered_cards = [card for card in ProductPage._cards_cache 
                            if card.product['category'] == category]
            
            # Add filtered cards in new positions
            for i, card in enumerate(filtered_cards):
                row = (i // 4) * 2
                col = i % 4
                self.grid_layout.addWidget(card, row, col)
                card.show()

        # Force layout update
        self.container.update()

    def return_to_welcome(self):
        """Return to welcome page using CART_END_SESSION_API"""
        try:
            # Call end session API
            response = requests.post(f"{CART_END_SESSION_API}{DEVICE_ID}/")
            if response.status_code == 200:
                # Clear phone number in JSON file
                try:
                    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                        'config', 'phone_number.json')
                    with open(file_path, 'w') as f:
                        json.dump({"phone_number": ""}, f)
                    print("Successfully cleared phone number")
                except Exception as e:
                    print(f"Error clearing phone number: {e}")
                    
                # Return to page1
                from page1_welcome import WelcomePage
                self.welcome_page = WelcomePage()
                self.welcome_page.show()
                self.close()
            else:
                print(f"Error ending session: {response.text}")
        except Exception as e:
            print(f"Error returning to welcome page: {e}")

    def show_product_modal(self, product):
        # Create overlay for blur effect
        self._overlay = QWidget(self)
        self._overlay.setGeometry(self.rect())
        self._overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
        self._overlay.show()
        
        # Create modal container
        self._modal = QFrame(self)
        self._modal.setFixedSize(350, 400)
        self._modal.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                border: none;
            }
        """)
        
        # Position modal in center of parent
        parent_rect = self.geometry()
        self._modal.move(
            (parent_rect.width() - self._modal.width()) // 2,
            (parent_rect.height() - self._modal.height()) // 2
        )
        
        # Create layout
        layout = QVBoxLayout(self._modal)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(5)  # Reduced spacing between components
        
        # Close button (X) at the top right
        close_btn = QPushButton("×")
        close_btn.setFixedSize(40, 40)  # Increased size
        close_btn.setFont(QFont("Arial", 16, QFont.Bold))  # Increased font size
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666;
                border: none;
                border-radius: 20px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                color: #333;
            }
        """)
        
        # Create a container for the close button
        close_container = QWidget()
        close_container.setStyleSheet("background-color: transparent;")
        close_layout = QHBoxLayout(close_container)
        close_layout.setContentsMargins(0, 0, 0, 0)
        close_layout.addStretch()
        close_layout.addWidget(close_btn)
        
        # Add close button container to main layout
        layout.addWidget(close_container)
        
        # Image with larger size to fit the modal
        image_label = QLabel()
        if product.get('image_url'):
            pixmap = SimpleImageLoader.load_image(product['image_url'], (180, 180))
            if pixmap:
                image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setStyleSheet("border: none;")
        layout.addWidget(image_label)
        
        # Name
        name = product['name'].replace('_', ' ')
        name_label = QLabel(name)
        name_label.setFont(QFont("Josefin Sans", 12, QFont.Bold))
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("border: none;")
        layout.addWidget(name_label)
        
        # Price
        price = "{:,.0f}".format(float(product['price'])).replace(',', '.')
        price_label = QLabel(f"{price} vnd")
        price_label.setFont(QFont("Josefin Sans", 10))
        price_label.setStyleSheet("color: #E72225; border: none;")
        price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(price_label)
        
        # Category
        category_label = QLabel(f"Category: {product['category']}")
        category_label.setFont(QFont("Josefin Sans", 12))
        category_label.setStyleSheet("color: black; border: none;")
        category_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(category_label)
        
        # Description
        desc_label = QLabel(product['description'])
        desc_label.setFont(QFont("Josefin Sans", 11))
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #666; border: none;")
        layout.addWidget(desc_label)
        
        # Connect close button
        close_btn.clicked.connect(self.close_modal)
        
        # Show modal and overlay
        self._modal.show()
        self._modal.raise_()
        
        # Handle click outside modal
        def handle_click(event):
            if not self._modal.geometry().contains(event.pos()):
                self.close_modal()
        
        self._overlay.mousePressEvent = handle_click

    def close_modal(self):
        if self._modal:
            self._modal.close()
            self._modal = None
        if self._overlay:
            self._overlay.close()
            self._overlay = None

class ProductCardDialog(QDialog):
    def __init__(self, product, image, parent=None):
        super().__init__(parent)
        self.product = product
        self.image = image
        self.setup_ui()
        
    def setup_ui(self):
        self.setFixedSize(400, 500)  # Increased dialog size
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 15px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Image
        image_label = QLabel()
        if self.image:
            image_label.setPixmap(self.image.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)
        
        # Name
        name = self.product['name'].replace('_', ' ')
        name_label = QLabel(name)
        name_label.setFont(QFont("Josefin Sans", 14, QFont.Bold))
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        # Price
        price = "{:,.0f}".format(float(self.product['price'])).replace(',', '.')
        price_label = QLabel(f"{price} vnd")
        price_label.setFont(QFont("Josefin Sans", 12))
        price_label.setStyleSheet("color: #E72225;")
        price_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(price_label)
        
        # Description
        desc_label = QLabel(self.product.get('description', 'No description available'))
        desc_label.setFont(QFont("Josefin Sans", 10))
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        # Add to Cart button
        add_to_cart_btn = QPushButton("Add to Cart")
        add_to_cart_btn.setFont(QFont("Josefin Sans", 12))
        add_to_cart_btn.setCursor(Qt.PointingHandCursor)
        add_to_cart_btn.setFixedHeight(30)
        add_to_cart_btn.setStyleSheet("""
            QPushButton {
                background-color: #507849;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 5px 10px;
                margin: 10px 20px;
            }
            QPushButton:hover {
                background-color: #3D6F4A;
            }
            QPushButton:pressed {
                background-color: #2C513A;
            }
        """)
        add_to_cart_btn.clicked.connect(lambda: self.parent().add_to_cart(self.product))
        layout.addWidget(add_to_cart_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFont(QFont("Josefin Sans", 12))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedHeight(30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E72225;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 5px 10px;
                margin: 10px 20px;
            }
            QPushButton:hover {
                background-color: #C41E3A;
            }
            QPushButton:pressed {
                background-color: #A31A32;
            }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    from count_item import add_cart_count_label, update_cart_count
    app = QApplication(sys.argv)
    product_page = ProductPage()
    add_cart_count_label(product_page)  # Thêm widget "Your Cart"
    product_page.show()
    sys.exit(app.exec_())